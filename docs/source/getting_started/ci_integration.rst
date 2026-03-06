.. _ci_integration:

CI Integration
==============

FlameIQ is designed to run in any CI system. The only requirements are
Python 3.10+ and the ability to run shell commands.

The critical pattern is:

1. **Cache** the ``.flameiq/`` directory keyed on the base branch
2. **Run** benchmarks on every commit
3. **Compare** against the cached baseline
4. **Upload** the HTML report as a build artefact

GitHub Actions
--------------

Minimal example
~~~~~~~~~~~~~~~

.. code-block:: yaml

   name: Performance Regression Check

   on:
     pull_request:
       branches: [main]
     push:
       branches: [main]

   jobs:
     benchmark:
       runs-on: ubuntu-latest

       steps:
         - uses: actions/checkout@v4

         - name: Set up Python
           uses: actions/setup-python@v5
           with:
             python-version: "3.12"

         - name: Install FlameIQ
           run: pip install flameiq-core

         - name: Restore baseline
           uses: actions/cache@v4
           with:
             path: .flameiq/
             key: flameiq-baseline-${{ github.base_ref || 'main' }}
             restore-keys: flameiq-baseline-

         - name: Run benchmarks
           run: python scripts/run_benchmarks.py > metrics.json

         - name: Set baseline on main pushes
           if: github.ref == 'refs/heads/main'
           run: flameiq baseline set --metrics metrics.json

         - name: Compare on pull requests
           if: github.event_name == 'pull_request'
           run: |
             flameiq compare \
               --metrics metrics.json \
               --fail-on-regression \
               --json | tee .flameiq/result.json

         - name: Generate report
           if: always()
           run: |
             flameiq report \
               --metrics metrics.json \
               --output .flameiq/report.html

         - name: Upload performance report
           if: always()
           uses: actions/upload-artifact@v4
           with:
             name: flameiq-report-${{ github.run_number }}
             path: |
               .flameiq/report.html
               .flameiq/result.json

Full matrix example (multiple environments)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: yaml

   jobs:
     benchmark:
       strategy:
         matrix:
           environment: [api, database, ml_inference]
       runs-on: ubuntu-latest

       steps:
         - uses: actions/checkout@v4
         - uses: actions/setup-python@v5
           with: { python-version: "3.12" }

         - run: pip install flameiq-core

         - name: Restore baseline
           uses: actions/cache@v4
           with:
             path: .flameiq/${{ matrix.environment }}/
             key: flameiq-${{ matrix.environment }}-${{ github.base_ref }}

         - name: Run ${{ matrix.environment }} benchmarks
           run: |
             python scripts/bench_${{ matrix.environment }}.py \
               > metrics_${{ matrix.environment }}.json

         - name: Compare ${{ matrix.environment }}
           run: |
             flameiq compare \
               --metrics metrics_${{ matrix.environment }}.json \
               --fail-on-regression

GitLab CI
---------

.. code-block:: yaml

   stages:
     - test
     - benchmark

   performance:
     stage: benchmark
     image: python:3.12-slim

     cache:
       key: "flameiq-${CI_DEFAULT_BRANCH}"
       paths:
         - .flameiq/

     script:
       - pip install flameiq-core --quiet
       - python scripts/run_benchmarks.py > metrics.json
       - |
         if [ "$CI_COMMIT_BRANCH" = "$CI_DEFAULT_BRANCH" ]; then
           flameiq baseline set --metrics metrics.json
         else
           flameiq compare --metrics metrics.json --fail-on-regression
         fi
       - flameiq report --metrics metrics.json --output report.html

     artifacts:
       when: always
       expire_in: 30 days
       paths:
         - report.html

Jenkins
-------

Declarative Pipeline
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: groovy

   pipeline {
       agent any

       stages {
           stage('Benchmark') {
               steps {
                   sh 'pip install flameiq-core --quiet'
                   sh 'python scripts/run_benchmarks.py > metrics.json'
               }
           }

           stage('Baseline (main only)') {
               when { branch 'main' }
               steps {
                   sh 'flameiq baseline set --metrics metrics.json'
               }
           }

           stage('Regression Check') {
               when { not { branch 'main' } }
               steps {
                   sh 'flameiq compare --metrics metrics.json --fail-on-regression'
               }
           }

           stage('Report') {
               steps {
                   sh 'flameiq report --metrics metrics.json --output report.html'
                   publishHTML([
                       reportDir: '.',
                       reportFiles: 'report.html',
                       reportName: 'FlameIQ Performance Report'
                   ])
               }
           }
       }
   }

CircleCI
--------

.. code-block:: yaml

   version: 2.1

   jobs:
     benchmark:
       docker:
         - image: cimg/python:3.12
       steps:
         - checkout

         - restore_cache:
             keys:
               - flameiq-v1-{{ .Branch }}
               - flameiq-v1-main

         - run:
             name: Install FlameIQ
             command: pip install flameiq-core

         - run:
             name: Run benchmarks
             command: python scripts/run_benchmarks.py > metrics.json

         - run:
             name: Regression check
             command: flameiq compare --metrics metrics.json --fail-on-regression

         - save_cache:
             key: flameiq-v1-{{ .Branch }}-{{ .Revision }}
             paths:
               - .flameiq/

         - store_artifacts:
             path: .flameiq/
             destination: flameiq

Storing baselines
-----------------

Baselines live in ``.flameiq/baselines/``. In CI, persist this directory
between runs using your system's cache mechanism, **keyed on the base branch**:

.. important::

   **Never commit** ``baselines/`` to your repository — it contains
   local machine measurements that vary by environment.

   ``flameiq init`` adds ``.flameiq/baselines/`` to ``.gitignore``
   automatically.

   For production quality, use a separate baseline per runner type
   if your CI runs on different machine sizes.

Exit codes
----------

All FlameIQ commands return standard CI exit codes:

.. list-table::
   :header-rows: 1
   :widths: 10 90

   * - Code
     - Meaning
   * - ``0``
     - Pass — no regression detected, or non-comparison command succeeded
   * - ``1``
     - Regression — one or more metrics exceeded threshold
   * - ``2``
     - Configuration or baseline error
   * - ``3``
     - Metrics file invalid or unreadable
