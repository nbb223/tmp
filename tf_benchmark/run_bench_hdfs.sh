#!/bin/bash

#### run as user 'dmo' ####

export HADOOP_HDFS_HOME=/memverge/home/songjue/hadoop-3.1.1
export CLASSPATH=$CLASSPATH:$(${HADOOP_HDFS_HOME}/bin/hadoop classpath --glob)

if [ $(hostname)  == 'maui' ]; then
    export CUDA_VISIBLE_DEVICES=0
elif [ $(hostname)  == 'bigisland' ]; then
    export CUDA_VISIBLE_DEVICES=1
fi

hdfs dfs -rm hdfs://aep0:4545/inception3_model_dir/*

cd ~songjue/tensorflow/benchmarks/scripts/tf_cnn_benchmarks
~songjue/anaconda3-gpu/bin/python tf_cnn_benchmarks.py \
		--save_model_steps=50 \
		--num_gpus=1 \
		--batch_size=32 \
		--model=inception3 \
		--variable_update=parameter_server \
		--data_dir=hdfs://aep0:4545/imageNet/tfrecord \
		--data_name=imagenet \
		--num_batches=500 \
		--train_dir=hdfs://aep0:4545/inception3_model_dir
		#--train_dir=/tmp/reNet-model-dir
		#--train_dir=/home/yli/nvme_ssd/songjue/renet_model_dir 

