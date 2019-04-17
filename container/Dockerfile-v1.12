FROM horovod/horovod:0.16.0-tf1.12.0-torch1.0.0-mxnet1.4.0-py3.5

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