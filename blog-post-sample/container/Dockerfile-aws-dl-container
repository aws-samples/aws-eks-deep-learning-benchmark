FROM 763104351884.dkr.ecr.us-east-1.amazonaws.com/tensorflow-training:1.13-horovod-gpu-py36-cu100-ubuntu16.04

RUN mkdir /code && git clone https://github.com/aws-samples/deep-learning-models.git /code

WORKDIR "/code"

CMD mpirun \
  python models/resnet/tensorflow/train_imagenet_resnet_hvd.py \
    --batch_size=256 \
    --model=resnet50 \
    --num_batches=1000 \
    --fp16 \
    --lr_decay_mode=poly \
    --synthetic