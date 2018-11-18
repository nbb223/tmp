from __future__ import print_function

import pandas as pd
import tensorflow as tf
import numpy as np
import math

import time
from tensorflow.python.platform import tf_logging as logging

logging._get_logger().setLevel(logging.INFO)
start = time.time()

# ### prameters to adjust:

# In[ ]:


hidden_units = [128,64,32] 
learning_rate = 0.001
batch_size = 7000
num_epochs = 5
l1_regularization_strength = 0.001
NUM_PARALLEL_BATCHES = 100
hash_bucket_size = 200

#filenames = ["hdfs://aep0:4545/census_extended/exp1.csv", "hdfs://aep0:4545/census_extended/exp2.csv", "hdfs://aep0:4545/census_extended/exp3.csv", "hdfs://aep0:4545/census_extended/exp4.csv", "hdfs://aep0:4545/census_extended/exp5.csv"]
filenames = ['./sparse.csv']
#filenames = ["hdfs://aep0:4545/census_extended/exp1.csv"]
target = 'label'
delim = ','
label_vocabulary = ["0", "1"]

#model_dir = 'hdfs://aep0:4545/model_dir/model'
model_dir = '~/model_linkedin'
tf.app.flags.DEFINE_string("num_workers", "", "num of workers")
tf.app.flags.DEFINE_string("worker_idx", "", "index of worker")
FLAGS = tf.app.flags.FLAGS

label_cols = {target: 6}

DEEP_FEATURE_DIMS = 3000
WIDE_FEATURE_DIMS = 100
NON_ZERO_NUM = 10

BATCH_IDX = np.array([ i for i in range(batch_size)])

features_deep = ['d0', 'd1', 'd2', 'd3', 'd4']
features_wide = ['w1']
default_value = [[""]] * 7
feature_cols = {'w1':0, 'd0':1, 'd1':2, 'd2':3, 'd3':4, 'd4':5}
'''
for i in df.columns:
    default_value += [[""]]
'''
# calculate emb_dim
emb_dim = []
for c in features_deep:
#    emb_dim.append(int(math.log(len(df[c].unique()), 2)))
    emb_dim.append(32)
#print(emb_dim)

deep_cols = []
count = 0
for col in features_deep:
    col = tf.feature_column.categorical_column_with_hash_bucket(col, hash_bucket_size=hash_bucket_size)
    deep_cols.append(tf.feature_column.embedding_column(col, emb_dim[count]))
    count += 1

wide_cols = tf.feature_column.categorical_column_with_hash_bucket(features_wide[0], hash_bucket_size=hash_bucket_size)

def getBatches(filenames):
    '''
    def _contains(indexes, i):
        result = tf.SparseTensor(
            indexes.indices, tf.math.equal(indexes.values, str(i)), indexes.dense_shape)
        return tf.sparse_reduce_sum(tf.cast(result, tf.int32))
    '''
    def mk_wide(indices):
        def _gen_idx(row, x):
            return row, tf.to_int64(x[0])

        v = tf.reshape(tf.cast(tf.string_to_number(indices.values), tf.float32), [batch_size, 2])  #idx:value
        elems = (BATCH_IDX, v)
        idx = tf.map_fn(lambda x: _gen_idx(x[0], x[1]), elems=(BATCH_IDX, v), dtype=(tf.int64, tf.int64))
        idx = tf.transpose(idx)
        val = tf.map_fn(lambda x: x[1], elems=v)

        return tf.sparse.SparseTensor(indices=idx, values=val, dense_shape=[batch_size, WIDE_FEATURE_DIMS])


    def mk_deep(indexes):
        def _make_idx(row, cols):
            return tf.map_fn(lambda x: (row, x), elems=cols, dtype=(tf.int64, tf.int64))

        idx = tf.reshape(tf.cast(tf.string_to_number(indexes.values), tf.int64), [batch_size, NON_ZERO_NUM])
        elems = (BATCH_IDX, idx)
        alternate = tf.map_fn(lambda x: _make_idx(x[0], x[1]), elems, dtype=(tf.int64, tf.int64))
        alternate = tf.transpose(alternate)
        indices = tf.reshape(alternate, [batch_size * NON_ZERO_NUM, 2])

        val = np.array([1] * (batch_size * NON_ZERO_NUM), dtype='int64')
        return tf.sparse.SparseTensor(indices=indices,
                                      values=val,
                                      dense_shape=[batch_size, DEEP_FEATURE_DIMS])

    def _parse(k, x):
        indices = tf.string_split([x], ":")

        return tf.cond(tf.equal(k, 'w1'), mk_wide(indices), mk_deep(indices))

#        return [ tf.dtypes.as_string(_contains(indexes, i)) for i in range(DEEP_FEATURE_DIMS)]

    def parse_one_batch(records):
        columns = tf.decode_csv(records, default_value, field_delim=delim)
#        features = dict([(k, columns[v]) for k, v in feature_cols.items()])
        features = dict([(k, _parse(k, columns[v])) for k, v in feature_cols.items()])
        labels = [columns[v] for _, v in label_cols.items()]
        #labels = tf.stack(labels, axis=1)
        return features, labels

    d = tf.data.Dataset.from_tensor_slices(filenames)
  #  d = d.flat_map(lambda filename: tf.data.TextLineDataset(filename, buffer_size=10000).skip(1).shard(int(FLAGS.num_workers), int(FLAGS.worker_idx)))
    d = d.flat_map(lambda filename: tf.data.TextLineDataset(filename, buffer_size=10000).skip(1))

#    d = d.apply(tf.contrib.data.shuffle_and_repeat(buffer_size=10000, count=num_epochs))
    d = d.repeat(num_epochs)
    d = d.apply(tf.contrib.data.map_and_batch(parse_one_batch, batch_size, num_parallel_batches=NUM_PARALLEL_BATCHES))
    d = d.prefetch(1000)
    return d

config = tf.estimator.RunConfig()
config = config.replace(keep_checkpoint_max=5, save_checkpoints_steps=500)
#for Intel MKL tunning
session_config = tf.ConfigProto()
session_config.intra_op_parallelism_threads = 48
session_config.inter_op_parallelism_threads = 48
#session_config.log_device_placement = True
config = config.replace(session_config=session_config)

estimator = tf.estimator.DNNLinearCombinedClassifier(
    model_dir=model_dir,
    config=config,
    linear_feature_columns=wide_cols,
    dnn_feature_columns=deep_cols,
    dnn_hidden_units=hidden_units,
    n_classes=len(label_vocabulary), label_vocabulary=label_vocabulary)

estimator.train(input_fn=lambda:getBatches(filenames))

end = time.clock()
print("***** training finished, CPU time elapsed: ", end-start, " ******")
