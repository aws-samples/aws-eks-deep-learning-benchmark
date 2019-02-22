{
  global: {
    // User-defined global parameters; accessible to all component and environments, Ex:
    // replicas: 4,
  },
  components: {
    // Component-level parameters, defined initially from 'ks prototype use ...'
    // Each object below should correspond to a component in the components/ directory
    workflows: {
      name: "benchmark-20190222-4",
      namespace: "default",
      bucket: "dl-benchmark-resource",
      image: "seedjeffwan/benchmark-runner:latest",
      region: "us-west-2",
      az: "us-west-2",
      ami: "ami-095922d81242d0528",
      instanceType: "p2.xlarge",
      placementGroup: "true",
      clusterVersion: "1.11",
      githubSecretName: "github-token",
      githubSecretTokenKeyName: "GITHUB_TOKEN",
      s3SecretName: "aws-secret",
      s3SecretAccesskeyidKeyName: "AWS_ACCESS_KEY_ID",
      s3SecretSecretaccesskeyKeyName: "AWS_SECRET_ACCESS_KEY",
      nfsVolumeClaim: "benchmark-pvc",
      nfsVolume: "benchmark-pv",
      experiments: [
        {
          experiment: "experiment-20190221-1", 
          trainingJobPkg: "mpi-job",
          trainingJobPrototype: "mpi-job-custom",
          trainingJobConfig: "mpi/mpi-job-1.yaml"
        },
        {
          experiment: "experiment-20190221-2",
          trainingJobPkg: "mpi-job",
          trainingJobPrototype: "mpi-job-custom",
          trainingJobConfig: "mpi/mpi-job-2.yaml"
        },
        {
          experiment: "experiment-20190221-3", 
          trainingJobPkg: "mpi-job",
          trainingJobPrototype: "mpi-job-custom",
          trainingJobConfig: "mpi/mpi-job-4.yaml"
        },
        {
          experiment: "experiment-20190221-4", 
          trainingJobPkg: "mpi-job",
          trainingJobPrototype: "mpi-job-custom",
          trainingJobConfig: "mpi/mpi-job-8.yaml"
        },
      ],
    },
  },
}
