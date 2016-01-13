RosaLab ABF workers
===================

**Workers for building packages, processing repositories and etc.**

This describes the resources that make up the official Rosa ABF workers. If you have any problems or requests please contact [support](https://abf.rosalinux.ru/contact).

**Note: This Documentation is in a beta state. Breaking changes may occur.**

## Installation

    curl -L get.rvm.io | bash -s stable
    source /home/rosa/.rvm/scripts/rvm
    rvm install ruby-2.2.3
    rvm gemset create abf-worker
    rvm use ruby-2.2.3@abf-worker --default

    cd abf-worker
    bundle install

    vi config/application.yml

    ENV=production CURRENT_PATH=$PWD bundle exec rake abf_worker:start
