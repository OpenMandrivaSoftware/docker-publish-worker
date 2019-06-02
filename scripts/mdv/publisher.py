#!/usr/bin/env python
#-*- coding: utf-8 -*-
import requests
import re
import os
import json
import subprocess
import time

# static values
file_store_base = 'http://file-store.openmandriva.org'
key_server = 'pool.sks-keyservers.net'
OMV_key = 'BF81DE15'
gnupg_path = '/root/.gnupg'
use_debug_repo = 'true'
arches=['SRPMS', 'i686', 'x86_64', 'armv7hnl', 'aarch64', 'znver1', 'riscv64']

# i.e cooker
save_to_platform = os.environ.get('SAVE_TO_PLATFORM')
build_for_platform = os.environ.get('BUILD_FOR_PLATFORM')
repository_path = os.environ.get('PLATFORM_PATH')
repository_name = os.environ.get('REPOSITORY_NAME')
# RELEASE = true/false
released = os.environ.get('RELEASED')
# testing = true/false
testing = os.environ.get('TESTING')
save_to_platform = os.environ.get('SAVE_TO_PLATFORM')
repository_name = os.environ.get('REPOSITORY_NAME')

is_container = os.environ.get('IS_CONTAINER')
regenerate_metadata = os.environ.get('REGENERATE_METADATA')
# not need
start_sign_rpms = os.environ.get('START_SIGN_RPMS')
# main_folder="$repository_path"/"$arch"/"$repository_name"
#arch = 'x86_64'
#repository_path = repository_path + '/' + arch + '/' + repository_name 

build_id="$ID"

get_home = os.environ.get('HOME')
gpg_dir = get_home + '/.gnupg'
rpm_macro = get_home + '/.rpmmacros'

def download_hash(hashfile):
    with open(hashfile, 'r') as fp:
        lines = [line.strip() for line in fp]
        for hash1 in lines:
            fstore_json_url = '{}/api/v1/file_stores.json?hash={}'.format(file_store_base, hash1)
            fstore_file_url = '{}/api/v1/file_stores/{}'.format(file_store_base, hash1)
            resp = requests.get(fstore_json_url)
            if resp.status_code == 404:
                print('requested package [{}] not found'.format(fstore_json_url))
            if resp.status_code == 200:
                page = resp.content.decode('utf-8')
                page2 = json.loads(page)
                name = page2[0]['file_name']
                print("%s %s" % (name, fstore_file_url))
                # curl -O -L http://file-store.openmandriva.org/api/v1/file_stores/169a726a478251325230bf3aec3a8cc04444ed3b
                download_file = requests.get(fstore_file_url)
                with open(name, 'wb') as f:
                    f.write(download_file.content)


def key_stuff():
    key_is = ''
    if os.path.isdir(gpg_dir) and os.path.getsize(gpg_dir) > 0:
        try:
            p = subprocess.check_output(['/usr/bin/gpg', '--list-public-keys', '--homedir', gpg_dir])
            # last 8 symbols
            key_pattern = '([A0-Z9]{8}$)'
            omv_key = re.search(key_pattern, p.decode('utf-8'), re.MULTILINE)
            if omv_key:
                key_is = omv_key.group(0).lower()
                print('Key used to sign RPM files: [%s]' % (key_is))
                return key_is
        except subprocess.CalledProcessError as e:
            print(e.output)
            return key_is
    else:
        print("%s not found, skip signing" % gpg_dir)
        return key_is

def generate_rpmmacros():
    key_name = key_stuff()
    # need to remove current macro
    # sometimes we changing keypairs
    if os.path.exists(rpm_macro) and os.path.getsize(rpm_macro) > 0:
        os.remove(rpm_macro)
    # generate ~/.rpmmacros
    if key_name != "":
        try:
            with open(rpm_macro, 'a') as file:
               file.write('%_signature gpg\n')
               file.write('%_gpg_path {}\n'.format(gpg_dir))
               file.write('%_gpg_name {}\n'.format(key_name))
               file.write('%_gpgbin /usr/bin/gpg\n')
               file.write('%__gpg_check_password_cmd /bin/true\n')
               file.write('%__gpg /usr/bin/gpg\n')
               # long string
               file.write('%__gpg_sign_cmd %__gpg gpg --no-tty ' 
                          '--pinentry-mode loopback --no-armor --no-secmem-warning '
                          '--sign --detach-sign --passphrase-file {} --sign '
                          '--detach-sign --output %__signature_filename %__plaintext_filename\n'.format(gpg_dir + '/secret'))
               file.write('%_disable_source_fetch  0\n')
               return True
        except OSError:
            return False
    else:
        print("key is empty")
        return False


def sign_rpm(path):
    generate_rpmmacros()
#    download_hash('hash.txt')
    files = []
    for r, d, f in os.walk(path):
        for rpm in f:
            if '.rpm' in rpm:
                files.append(os.path.join(r, rpm))
    if os.path.exists(rpm_macro) and os.path.getsize(rpm_macro) > 0:
        for rpm in files:
            try:
                print('signing rpm %s' % rpm)
                p = subprocess.check_output(['rpm', '--addsign', rpm])
            except:
                print('something went wrong with signing rpm %s' % rpm)
                continue
    else:
        print("no key provided, signing disabled")

def repo_lock(path):
    while os.path.exists(path + '/.publish.lock'):
        print(".publish.lock exist, let wait a bit...")
        time.sleep(60)
    print("creating %s/.publish.lock" % path)
    open(path + '/.publish.lock', 'a').close()

def repo_unlock(path):
    print("removing %s/.publish.lock" % path)
    if os.path.exists(path + '/.publish.lock'):
       os.remove(path + '/.publish.lock')

def regenerate_metadata_repo(action):
    if released == 'false':
        status = 'release'
    if released == 'true':
        status = 'updates'
    if testing == 'true':
        status = 'testing'
    if action == 'regenerate':
        for arch in arches:
            path = repository_path + '/' + arch + '/' + repository_name + '/' + status
            # /share/platforms/cooker/repository/riscv64/main
            sign_rpm(path)
#            print("running metadata generator for %s" % path)
            # create .publish.lock
            repo_lock(path)
            try:
                p = subprocess.check_output(['/usr/bin/docker', 'run', '--rm', '-v', '/var/lib/openmandriva/abf-downloads:/share/platforms', 'openmandriva/createrepo', path, action])
                repo_unlock(path)
            except:
                print("something went wrong with publishing for %s" % path)
                repo_unlock(path)
    else:
        for arch in arches:
            path = repository_path + '/' + arch + '/' + repository_name + '/' + status
            # /share/platforms/cooker/repository/riscv64/main/release or testing or updates
            sign_rpm(path)
#            print("running metadata generator for %s" % path)
            # create .publish.lock
            repo_lock(path)
            try:
                p = subprocess.check_output(['/usr/bin/docker', 'run', '--rm', '-v', '/var/lib/openmandriva/abf-downloads:/share/platforms', 'openmandriva/createrepo', path, action])
                print('openmandriva/createrepo', path, action)
                repo_unlock(path)
            except:
                print("something went wrong with publishing for %s" % path)
                repo_unlock(path)


#regenerate_metadata_repo()

if __name__ == '__main__':
    if regenerate_metadata == 'true':
        regenerate_metadata_repo('regenerate')
    if regenerate_metadata == '':
        regenerate_metadata_repo('')
