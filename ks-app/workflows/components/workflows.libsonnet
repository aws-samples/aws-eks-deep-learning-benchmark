{
  buildArgoBenchmarkStep:: function(e) {
    result::
    {
      name: e.experiment,
      template: e.experiment,
    },
  }.result,

  awsParams:: {
    //  Name of the k8s secrets containing S3 credentials
    awsSecretName: "",
    // Name of the key in the k8s secret containing AWS_ACCESS_KEY_ID.
    awsSecretAccesskeyidKeyName: "AWS_ACCESS_KEY_ID",
    // Name of the key in the k8s secret containing AWS_SECRET_ACCESS_KEY.
    awsSecretSecretaccesskeyKeyName: "AWS_SECRET_ACCESS_KEY",
    // S3 region
    awsRegion: "us-west-2",
    // true Whether or not to use https for S3 connections
    s3UseHttps: "true",
    // Whether or not to verify https certificates for S3 connections
    s3VerifySsl: "true",
    // URL for your s3-compatible endpoint.
    s3Endpoint: "s3.us-west-1.amazonaws.com",
  },


  // The name of test cluster
  //local clusterName = "kubebench-e2e-" + std.substr(name, std.length(name) - 4, 4),
  // The Kubernetes version of test cluster
  local clusterVersion = "1.11",

  new(_env, _params):: {
    local params = _params + _env,

    // Fixed names won't change. Doesn't need to be passed from params
    // mountPath is the directory where the volume to store the test data
    // should be mounted.
    local mountPath = "/mnt/benchmark",
    // benchmarkDir is the root directory for all data for a particular test run.
    local benchmarkDir = mountPath + "/" + params.name,
    // benchmarkOutputDir is the directory to sync to GCS to contain the output for this job.
    local benchmarkOutputDir = benchmarkDir + "/output",
    local benchmarkArtifactsDir =  benchmarkOutputDir + "/artifacts",
    // Source directory where all repos should be checked out
    local benchmarkSrcRootDir = benchmarkDir + "/src",
    local benchmarkKubeConfigPath = benchmarkDir + "/kubeconfig",
    local srcDir = benchmarkSrcRootDir + "/jeffwan/ml-benchmark",
    // The directory containing the py scripts for testing
    local srcTestPyDir = srcDir + "/src",
    // The directory within the kubeflow_testing submodule containing
    // py scripts to use.
    local srcKubeTestPyDir = benchmarkSrcRootDir + "/kubeflow/testing/py",
    // The name of the NFS volume claim to use for test files.
    // local nfsVolumeClaim = "kubeflow-testing";
    local nfsVolumeClaim = params.nfsVolumeClaim,
    // The name to use for the volume to use to contain test data.
    local dataVolume = params.nfsVolume,

    // The training dataset volume
    local trainingDatasetVolume = params.trainingDatasetVolume,

    local enableDatasetStorage = if (params.storageBackend == "fsx") || (params.storageBackend == "efs") then true else false,
    // Only EFS need to copy data, FSx use S3 data repository support in creation
    local needDataCopy = if enableDatasetStorage && (params.storageBackend == "efs") then true else false,

    // Optional
    local placementGroup = if params.placementGroup == "true" then
      "--placement_group"
    else
      "--no-placement_group",

    // this combination will guarantee aws SDK working properly
    local aws_credential_env = [
      {
          name: "AWS_ACCESS_KEY_ID",
          valueFrom: {
            secretKeyRef: {
              name: params.s3SecretName,
              key: params.s3SecretAccesskeyidKeyName,
            },
          },
        },
        {
          name: "AWS_SECRET_ACCESS_KEY",
          valueFrom: {
            secretKeyRef: {
              name: params.s3SecretName,
              key: params.s3SecretSecretaccesskeyKeyName,
            },
          },
        },
        {
          name: "AWS_DEFAULT_REGION",
          value: params.region
        },
    ],

    local github_token_env = [
      {
        name: "GITHUB_TOKEN",
        valueFrom: {
          secretKeyRef: {
            name: params.githubSecretName,
            key: params.githubSecretTokenKeyName,
          },
        },
      }
    ],

    local buildBenchmarkTemplate = function(e) {
      result::
        $.new(_env, _params).buildTemplate(e.experiment, [
            "python",
            "-m",
            "benchmark.test.run_benchmark_job",
            "--base_dir=" + benchmarkDir,
            "--namespace=" + params.namespace,
            "--experiment_name=" + e.experiment,
            "--training_job_pkg=" + e.trainingJobPkg,
            "--training_job_prototype=" + e.trainingJobPrototype,
            "--training_job_config=" + e.trainingJobConfig,
            "--training_job_registry=" + e.trainingJobRegistry,
            "--data_pvc=" + trainingDatasetVolume
          ], envVars=github_token_env + aws_credential_env,
        ),  // run kubebench job
    }.result,

    local benchmarksteps = std.map(buildBenchmarkTemplate, params.experiments),

    // Build an Argo step template to execute a particular command.
    // step_name: Name for the template
    // command: List to pass as the container command.
    buildTemplate(step_name, command, envVars=[], sidecars=[], workingDir=null, kubeConfig="config"):: {
      name: step_name,
      container: {
        command: command,
        image: params.image,
        [if workingDir != null then "workingDir"]: workingDir,
        env: [
          {
            name: "BENCHMARK_DIR",
            value: benchmarkDir
          },
          {
            // Add the source directories to the python path.
            name: "PYTHONPATH",
            value: srcTestPyDir + ":" + srcKubeTestPyDir,
          },
          {
            // We use a directory in our NFS share to store our kube config.
            // This way we can configure it on a single step and reuse it on subsequent steps.
            name: "KUBECONFIG",
            value: benchmarkKubeConfigPath,
          },
        ] + envVars,
        volumeMounts: [
          {
            name: dataVolume,
            mountPath: mountPath,
          },
        ],
      },
      sidecars: sidecars,
    },  // buildTemplate

    // Workflow to run the e2e test.
    benchmark:: {
      apiVersion: "argoproj.io/v1alpha1",
      kind: "Workflow",
      metadata: {
        name: params.name,
        namespace: params.namespace,
      },
      spec: {
        entrypoint: "benchmark",
        volumes: [
          {
            name: dataVolume,
            persistentVolumeClaim: {
              claimName: nfsVolumeClaim,
            },
          },
        ],  // volumes
        // onExit specifies the template that should always run when the workflow completes.
        onExit: "exit-handler",
        templates: [
          {
            name: "benchmark",
            steps: [
              [
                {
                  name: "checkout",
                  template: "checkout",
                },
              ],
              [
                {
                  name: "create-cluster",
                  template: "create-cluster",
                },
              ],
              [
                {
                  name: "install-gpu-driver",
                  template: "install-gpu-driver",
                },
                {
                  name: "install-kubeflow",
                  template: "install-kubeflow",
                },
                {
                  name: "install-github-secret",
                  template: "install-github-secret",
                },
                {
                  name: "install-aws-secret",
                  template: "install-aws-secret",
                },
                if enableDatasetStorage then
                {
                  name: "install-storage-backend",
                  template: "install-storage-backend",
                }
                else {},
              ],
              [
                {
                  name: "install-storage-driver",
                  template: "install-storage-driver",
                },
              ],
              [ if needDataCopy then
                {
                  name: "copy-dataset",
                  template: "copy-dataset",
                } else {},
              ],
              std.map($.buildArgoBenchmarkStep, params.experiments),
            ],
          },
          {
            name: "exit-handler",
            steps: [
              [
                {
                  name: "copy-results",
                  template: "copy-results",
                },
                if enableDatasetStorage then
                {
                  name: "uninstall-storage-backend",
                  template: "uninstall-storage-backend",
                } else {},
              ],
              [
                {
                  name: "teardown-cluster",
                  template: "teardown-cluster",
                },
              ],
              [
                {
                  name: "delete-test-dir",
                  template: "delete-test-dir",
                },
              ],
            ],
          },
          $.new(_env, _params).buildTemplate(
            "checkout",
            ["sh", "/usr/local/bin/download_source.sh", benchmarkSrcRootDir, "master"],
          ),  // checkout

          $.new(_env, _params).buildTemplate("create-cluster", [
            "python",
            "-m",
            "benchmark.test.create_cluster",
            "--region=" + params.region,
            "--cluster_name=" + params.name,
            "--cluster_config=" + params.clusterConfig,
          ], envVars=aws_credential_env
          ),  // create cluster

          $.new(_env, _params).buildTemplate("install-gpu-driver", [
            "python",
            "-m",
            "benchmark.test.install_gpu_driver",
            "--base_dir=" + benchmarkDir,
            "--namespace=" + params.namespace,
          ], envVars=github_token_env + aws_credential_env
          ),  // install gpu driver

          $.new(_env, _params).buildTemplate("install-kubeflow", [
            "python",
            "-m",
            "benchmark.test.install_kubeflow",
            "--base_dir=" + benchmarkDir,
            "--namespace=" + params.namespace,
            "--kubeflow_registry=" + params.kubeflowRegistry,
          ], envVars=github_token_env + aws_credential_env
          ),  // install kubeflow

          $.new(_env, _params).buildTemplate("install-github-secret", [
            "python",
            "-m",
            "benchmark.test.install_github_secret",
            "--namespace=" + params.namespace,
            "--github-secret-name=" + params.githubSecretName,
          ], envVars=github_token_env + aws_credential_env
          ),  // install github secret

          $.new(_env, _params).buildTemplate("install-aws-secret", [
            "python",
            "-m",
            "benchmark.test.install_aws_secret",
            "--namespace=" + params.namespace,
          ], envVars=aws_credential_env
          ),  // install github secret

          $.new(_env, _params).buildTemplate("install-storage-backend", [
            "python",
            "-m",
            "benchmark.test.install_storage_backend",
            "--base_dir=" + benchmarkDir,
            "--storage_backend=" + params.storageBackend,
            "--s3_import_path=" + params.s3DatasetPath,
            "--experiment_id=" + params.name,
          ], envVars= aws_credential_env
          ),  // install storage backend

          $.new(_env, _params).buildTemplate("uninstall-storage-backend", [
            "python",
            "-m",
            "benchmark.test.uninstall_storage_backend",
            "--base_dir=" + benchmarkDir,
            "--storage_backend=" + params.storageBackend,
            "--experiment_id=" + params.name,
          ], envVars= aws_credential_env
          ),  // uninstall storage backend

          $.new(_env, _params).buildTemplate("install-storage-driver",[
            "python",
            "-m",
            "benchmark.test.install_storage_driver",
            "--base_dir=" + benchmarkDir,
            "--storage_backend=" + params.storageBackend,
          ], envVars=aws_credential_env,
          ),  // install storage driver

          $.new(_env, _params).buildTemplate("copy-dataset", [
            "python",
            "-m",
            "benchmark.test.copy_dataset",
            "--s3_import_path=" + params.s3DatasetPath,
            "--pvc=" + trainingDatasetVolume,
            "--region=" + params.region,
            "--namespace=" + params.namespace,
            "--runner_image=" + params.image
          ], envVars=aws_credential_env
          ),  // copy-dataset

          $.new(_env, _params).buildTemplate("copy-results", [
            "sh", srcDir + "/src/benchmark/test/copy_results.sh", params.namespace, params.s3ResultPath,
          ], envVars=aws_credential_env
          ),  // copy-results

          $.new(_env, _params).buildTemplate("teardown-cluster", [
            "python",
            "-m",
            "benchmark.test.delete_cluster",
          ], envVars=aws_credential_env,
          ),  // teardown cluster

          $.new(_env, _params).buildTemplate("delete-test-dir", [
            "bash",
            "-c",
            "rm -rf " + benchmarkDir,
          ]),  // delete test dir
        ] + benchmarksteps,  // templates
      }, // spec
    },  // benchmark
  },  // parts
}
