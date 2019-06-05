#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
import re
import os
import json
import subprocess
import time
import shutil
# RELEASED=false REPOSITORY_NAME=main PLATFORM_PATH=/share/platforms/cooker/repository REGENERATE_METADATA= python publisher.py

# static values
file_store_base = 'http://file-store.openmandriva.org'
key_server = 'pool.sks-keyservers.net'
OMV_key = 'BF81DE15'
gnupg_path = '/root/.gnupg'
use_debug_repo = 'true'
arches = ['SRPMS', 'i686', 'x86_64',
          'armv7hnl', 'aarch64', 'znver1', 'riscv64']

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
# arch = 'x86_64'
# repository_path = repository_path + '/' + arch + '/' + repository_name

build_id = "$ID"

get_home = os.environ.get('HOME')
gpg_dir = get_home + '/.gnupg'
rpm_macro = get_home + '/.rpmmacros'
# /root/docker-publish-worker/container
container_path = get_home + '/docker-publish-worker/container'

if released == 'false':
    status = 'release'
if released == 'true':
    status = 'updates'
if testing == 'true':
    status = 'testing'


def download_hash(hashfile):
    with open(hashfile, 'r') as fp:
        lines = [line.strip() for line in fp]
        for hash1 in lines:
            fstore_json_url = '{}/api/v1/file_stores.json?hash={}'.format(
                file_store_base, hash1)
            fstore_file_url = '{}/api/v1/file_stores/{}'.format(
                file_store_base, hash1)
            resp = requests.get(fstore_json_url)
            if resp.status_code == 404:
                print('requested package [{}] not found'.format(
                    fstore_json_url))
            if resp.status_code == 200:
                page = resp.content.decode('utf-8')
                page2 = json.loads(page)
                name = page2[0]['file_name']
                print("%s %s" % (name, fstore_file_url))
                # curl -O -L http://file-store.openmandriva.org/api/v1/file_stores/169a726a478251325230bf3aec3a8cc04444ed3b
                download_file = requests.get(fstore_file_url)
                tmpname = '/tmp/' + name
                with open(tmpname, 'wb') as f:
                    f.write(download_file.content)


def key_stuff():
    key_is = ''
    if os.path.isdir(gpg_dir) and os.path.getsize(gpg_dir) > 0:
        try:
            p = subprocess.check_output(
                ['/usr/bin/gpg', '--list-public-keys', '--homedir', gpg_dir])
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
                subprocess.check_output(['rpm', '--addsign', rpm])
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


def backup_rpms(old_list, backup_repo):
    arch = old_list.split('.')
    repo = repository_path + '/' + arch[1] + \
        '/' + repository_name + '/' + status
    debug_repo = repository_path + '/' + \
        arch[1] + '/' + 'debug_' + repository_name + '/' + status
    backup_debug_repo = repository_path + '/' + \
        arch[1] + '/' + 'debug_' + repository_name + \
        '/' + status + '-rpm-backup/'
    if os.path.exists(backup_repo) and os.path.isdir(backup_repo):
        shutil.rmtree(backup_repo)
    if os.path.exists(backup_debug_repo) and os.path.isdir(backup_debug_repo):
        shutil.rmtree(backup_debug_repo)

    if os.path.exists(old_list) and os.path.getsize(old_list) > 0:
        with open(old_list, 'r') as fp:
            lines = [line.strip() for line in fp]
            if not os.path.exists(backup_repo):
                os.makedirs(backup_repo)
            if not os.path.exists(backup_debug_repo):
                os.makedirs(backup_debug_repo)
            for rpm in lines:
                if 'debuginfo' in rpm:
                    if os.path.exists(debug_repo + '/' + rpm):
                        print("moving %s to %s" % (rpm, backup_repo))
                        shutil.move(debug_repo + '/' + rpm, backup_debug_repo)
                if os.path.exists(repo + '/' + rpm):
                    print("moving %s to %s" % (rpm, backup_repo))
                    shutil.move(repo + '/' + rpm, backup_repo)


def prepare_rpms():
    sourcepath = '/tmp/'
    files = [f for f in os.listdir(
        container_path) if re.match(r'new.(.*)\.list$', f)]
    arches = [i.split('.', 2)[1] for i in files]
    print(arches)
    for arch in arches:
        # /root/docker-publish-worker/container/new.riscv64.list
        rpm_arch_list = container_path + '/' + 'new.' + arch + '.list'
        # old.SRPMS.list
        rpm_old_list = container_path + '/' + 'old.' + arch + '.list'
        # /share/platforms/rolling/repository/SRPMS/main/release-rpm-new/
        tiny_repo = repository_path + '/' + arch + '/' + \
            repository_name + '/' + status + '-rpm-new/'
        # backup repo for rollaback
        backup_repo = repository_path + '/' + arch + '/' + \
            repository_name + '/' + status + '-rpm-backup/'
        backup_debug_repo = repository_path + '/' + arch + '/' + \
            'debug_' + repository_name + '/' + status + '-rpm-backup/'
        repo = repository_path + '/' + arch + '/' + repository_name + '/' + status
        debug_repo = repository_path + '/' + arch + '/' + \
            'debug_' + repository_name + '/' + status
        backup_rpms(rpm_old_list, backup_repo)
        for r, d, f in os.walk(sourcepath):
            for rpm in f:
                if '.rpm' in rpm:
                    os.remove(sourcepath + rpm)
        if os.path.exists(rpm_arch_list) and os.path.getsize(rpm_arch_list) > 0:
            download_hash(rpm_arch_list)
            source = os.listdir(sourcepath)
            for files in source:
                if files.endswith('.rpm'):
                    # target dir + foo.x86_64.rpm to dir
                    if not os.path.exists(tiny_repo):
                        os.makedirs(tiny_repo)
                    shutil.copy(sourcepath + files, tiny_repo)
            sign_rpm(tiny_repo)
            for rpm in os.listdir(tiny_repo):
                # move all rpm filex exclude debuginfo
                if 'debuginfo' not in rpm:
                    print("moving %s to %s" % (rpm, repo))
                    shutil.copy(tiny_repo + rpm, repo)
            repo_lock(repo)
            try:
                subprocess.check_output(['/usr/bin/docker', 'run', '--rm', '-v',
                                         '/var/lib/openmandriva/abf-downloads:/share/platforms', 'openmandriva/createrepo', repo])
                repo_unlock(repo)
            except:
                print('publishing failed, rollbacking rpms')
                repo_unlock(repo)
                # rollback rpms
                shutil.copy(backup_repo + rpm, repo)

                # rollback rpms
            # move debuginfo in place
            for debug_rpm in os.listdir(tiny_repo):
                if 'debuginfo' in debug_rpm:
                    print("moving %s to %s" % (debug_rpm, debug_repo))
                    shutil.copy(tiny_repo + debug_rpm, debug_repo)
            if os.path.exists(debug_repo):
                repo_lock(debug_repo)
                try:
                    subprocess.check_output(
                        ['/usr/bin/docker', 'run', '--rm', '-v', '/var/lib/openmandriva/abf-downloads:/share/platforms', 'openmandriva/createrepo', debug_repo])
                    repo_unlock(debug_repo)
                except:
                    print('publishing failed, rollbacking rpms')
                    repo_unlock(debug_repo)
                    # rollback rpms
                    shutil.copy(backup_debug_repo + debug_rpm, debug_repo)
            shutil.rmtree(tiny_repo)


def regenerate_metadata_repo(action):
    if action == 'regenerate':
        for arch in arches:
            path = repository_path + '/' + arch + '/' + repository_name + '/' + status
            # /share/platforms/rolling/repository/i686/main/release-rpm-new
            # /share/platforms/cooker/repository/riscv64/main
            sign_rpm(path)
#            print("running metadata generator for %s" % path)
            # create .publish.lock
            repo_lock(path)
            try:
                subprocess.check_output(['/usr/bin/docker', 'run', '--rm', '-v',
                                         '/var/lib/openmandriva/abf-downloads:/share/platforms', 'openmandriva/createrepo', path, action])
                repo_unlock(path)
            except:
                print("something went wrong with publishing for %s" % path)
                repo_unlock(path)
    else:
        for arch in arches:
            path = repository_path + '/' + arch + '/' + repository_name + '/' + status
            # /share/platforms/cooker/repository/riscv64/main
            sign_rpm(path)
#            print("running metadata generator for %s" % path)
            # create .publish.lock
            repo_lock(path)
            try:
                subprocess.check_output(['/usr/bin/docker', 'run', '--rm', '-v',
                                         '/var/lib/openmandriva/abf-downloads:/share/platforms', 'openmandriva/createrepo', path, action])
                repo_unlock(path)
            except:
                print("something went wrong with publishing for %s" % path)
                repo_unlock(path)


# regenerate_metadata_repo()

if __name__ == '__main__':
    if regenerate_metadata == 'true':
        regenerate_metadata_repo('regenerate')
    if regenerate_metadata == '':
        prepare_rpms()
