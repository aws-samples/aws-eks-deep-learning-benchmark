{
  global: {},
  components: {
    // Component-level parameters, defined initially from 'ks prototype use ...'
    // Each object below should correspond to a component in the components/ directory
    workflows: {
      s3ResultPath: 's3://kubeflow-pipeline-data/benchmark/',
      s3DatasetPath: 's3://eks-dl-benchmark/imagenet/',
      clusterConfig: 's3://kubeflow-pipeline-data/benchmark/cluster_config.yaml',
      experiments: [{
        experiment: 'experiment-20190415-01',
        trainingJobConfig: 's3://kubeflow-pipeline-data/benchmark/mpi-job-imagenet.yaml',
        trainingJobPkg: 'mpi-job',
        trainingJobPrototype: 'mpi-job-custom',
        trainingJobRegistry: 'github.com/jeffwan/kubeflow/tree/make_kubebench_reporter_optional/kubeflow',
      }],
      githubSecretName: 'github-token',
      githubSecretTokenKeyName: 'GITHUB_TOKEN',
      image: 'seedjeffwan/benchmark-runner:20190415-fix',
      name: '20190415-07',
      namespace: 'default',
      nfsVolume: 'benchmark-pv',
      nfsVolumeClaim: 'benchmark-pvc',
      region: 'us-west-2',
      trainingDatasetVolume: 'dataset-claim', # should pass to storage pvc name
      s3SecretName: 'aws-secret',
      s3SecretAccesskeyidKeyName: 'AWS_ACCESS_KEY_ID',
      s3SecretSecretaccesskeyKeyName: 'AWS_SECRET_ACCESS_KEY',
      storageBackend: 'fsx',
      kubeflowRegistry: 'github.com/jeffwan/kubeflow/tree/make_kubebench_reporter_optional/kubeflow'
    },
  },
}
