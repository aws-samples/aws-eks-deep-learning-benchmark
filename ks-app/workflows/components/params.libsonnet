{
  global: {},
  components: {
    // Component-level parameters, defined initially from 'ks prototype use ...'
    // Each object below should correspond to a component in the components/ directory
    workflows: {
      ami: 'ami-095922d81242d0528',
      az: 'us-west-2a',
      s3ResultBucket: 'dl-benchmark-result',
      s3DatasetBucket: 'eks-dl-benchmark',
      clusterVersion: '1.11',
      experiments: [{
        experiment: 'experiment-20190327-11',
        trainingJobConfig: 'mpi/mpi-job-dummy.yaml',
        trainingJobPkg: 'mpi-job',
        trainingJobPrototype: 'mpi-job-custom',
      }],
      githubSecretName: 'github-token',
      githubSecretTokenKeyName: 'GITHUB_TOKEN',
      image: 'seedjeffwan/benchmark-runner:latest',
      instanceType: 'p3.2xlarge',
      nodeCount: 1,
      name: '20190329-01',
      namespace: 'default',
      nfsVolume: 'benchmark-pv',
      nfsVolumeClaim: 'benchmark-pvc',
      placementGroup: 'true',
      region: 'us-west-2',
      s3SecretName: 'aws-secret',
      s3SecretAccesskeyidKeyName: 'AWS_ACCESS_KEY_ID',
      s3SecretSecretaccesskeyKeyName: 'AWS_SECRET_ACCESS_KEY',
      storageBackend: 'fsx',
    },
  },
}