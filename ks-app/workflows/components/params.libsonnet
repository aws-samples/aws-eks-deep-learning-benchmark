{
  global: {},
  components: {
    // Component-level parameters, defined initially from 'ks prototype use ...'
    // Each object below should correspond to a component in the components/ directory
    workflows: {
      ami: 'ami-08377056d89909b2a',
      az: 'us-west-2a',
      zones: 'us-test-2a,us-west-2b,us-west-2c',
      s3ResultPath: 's3://kubeflow-pipeline-data/benchmark/',
      s3DatasetPath: 's3://eks-dl-benchmark',
      clusterVersion: '1.11',
      #clusterConfig: 's3://kubeflow-pipeline-data/benchmark/cluster_config.yaml',
      experiments: [{
        experiment: 'experiment-20190327-11',
        trainingJobConfig: 's3://kubeflow-pipeline-data/benchmark/mpi-job-imagenet.yaml',
        trainingJobPkg: 'mpi-job',
        trainingJobPrototype: 'mpi-job-custom',
        trainingJobRegistry: 'github.com/jeffwan/kubeflow/tree/make_kubebench_reporter_optional/kubeflow',
      }],
      githubSecretName: 'github-token',
      githubSecretTokenKeyName: 'GITHUB_TOKEN',
      image: 'seedjeffwan/benchmark-runner:latest',
      instanceType: 'p3.2xlarge',
      nodeCount: 1,
      name: '20190415-02',
      namespace: 'default',
      nfsVolume: 'benchmark-pv',
      nfsVolumeClaim: 'benchmark-pvc',
      placementGroup: 'true',
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
