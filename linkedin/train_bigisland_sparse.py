from __future__ import print_function

import pandas as pd
import tensorflow as tf
import numpy as np
import math
import sys
import time
from tensorflow.python.platform import tf_logging as logging

tf.enable_eager_execution()

logging._get_logger().setLevel(logging.INFO)
start = time.time()

hidden_units = [128,64,32]
learning_rate = 0.001
batch_size = 1
num_epochs = 1
l1_regularization_strength = 0.001
NUM_PARALLEL_BATCHES = 1
hash_bucket_size = 200

filenames = r"C:\Users\songjue\works\linkedin\sparse.csv"
target = 'label'
delim = ','
label_vocabulary = ["0", "1"]

model_dir = 'model_linkedin'

label_cols = {target: 6}

DEEP_FEATURE_DIMS = 3000
WIDE_FEATURE_DIMS = 100
NON_ZERO_NUM = 10

BATCH_IDX = np.array([ i for i in range(batch_size)])

features_deep = ['d0', 'd1', 'd2', 'd3', 'd4']
features_wide = ['w1']
default_value = [[""]] * 7
feature_cols = {'w1':0, 'd0':1, 'd1':2, 'd2':3, 'd3':4, 'd4':5}
#feature_cols = {'w1':0}

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
#deep_cols=deep_cols[0]
wide_cols = tf.feature_column.categorical_column_with_hash_bucket(features_wide[0], hash_bucket_size=hash_bucket_size)


def getBatches(filenames):
    def mk_wide(indices):
        def _gen_idx(row, x):
            return row, tf.to_int64(x[0])

        v = tf.reshape(tf.cast(tf.string_to_number(indices.values), tf.float32), [batch_size, 2])  # idx:value
        elems = (BATCH_IDX, v)
        idx = tf.map_fn(lambda x: _gen_idx(x[0], x[1]), elems=(BATCH_IDX, v), dtype=(tf.int64, tf.int64))
        idx = tf.transpose(idx)
        val = tf.map_fn(lambda x: x[1], elems=tf.dtypes.as_string(v))

        return tf.sparse.SparseTensor(indices=idx, values=val, dense_shape=[batch_size, WIDE_FEATURE_DIMS])

    def mk_deep(indexes):
        def _make_idx(row, cols):
            return tf.map_fn(lambda x: (row, x), elems=cols, dtype=(tf.int64, tf.int64))

        idx = tf.reshape(tf.cast(tf.string_to_number(indexes.values), tf.int64), [batch_size, NON_ZERO_NUM])
        elems = (BATCH_IDX, idx)
        alternate = tf.map_fn(lambda x: _make_idx(x[0], x[1]), elems, dtype=(tf.int64, tf.int64))
        alternate = tf.transpose(alternate)
        indices = tf.reshape(alternate, [batch_size * NON_ZERO_NUM, 2])

        val = np.array(['1'] * (batch_size * NON_ZERO_NUM))  # , dtype='int64')
        return tf.sparse_reorder(tf.sparse.SparseTensor(indices=indices,
                                                        values=val,
                                                        dense_shape=[batch_size, DEEP_FEATURE_DIMS]))

    def _parse(k, x):
        # print(eval(x))
        # print(x)
        indices = tf.string_split([x], ":")
        return tf.cond(pred=tf.equal(k, 'w1'),
                       true_fn=lambda: mk_wide(indices),  # lambda is a must as true_fn/false_fn expects a callable
                       false_fn=lambda: mk_deep(indices))

        # return indices

    def parse_one_batch(records):
        print(records)
        columns = tf.decode_csv(records, default_value, field_delim=delim)

        features = dict([(k, _parse(k, columns[v])) for k, v in feature_cols.items()])

        # features = dict([(k, columns[v]) for k, v in feature_cols.items()])

        labels = [columns[v] for _, v in label_cols.items()]
        #   return labels
        return features, labels

    # d = tf.data.Dataset.from_tensor_slices(filenames)
    #  d = d.flat_map(lambda filename: tf.data.TextLineDataset(filename, buffer_size=10000).skip(1).shard(int(FLAGS.num_workers), int(FLAGS.worker_idx)))
    # d = d.flat_map(lambda filename: tf.data.TextLineDataset(filename, buffer_size=10000).skip(1))

    d = tf.data.TextLineDataset(filenames, buffer_size=10000).skip(1)

    # d = d.repeat(num_epochs)
    d = d.apply(
        tf.data.experimental.map_and_batch(parse_one_batch, batch_size, num_parallel_batches=NUM_PARALLEL_BATCHES))
    d = d.prefetch(1000)

    return d

#######################
d = getBatches(filenames)
#d = tf.data.TextLineDataset(filenames, buffer_size=10000).skip(1)
iterator = d.make_one_shot_iterator()
f, l = iterator.get_next()

sess = tf.Session()
while True:
    try:
        print(sess.run(f['w1']))   #convert Bytes to String
        print("------------------------")
 #   except tf.errors.OutOfRangeError:
 #       break
    except:
        e = sys.exc_info()[0]
        print("<p>Error: %s</p>" % e )
        break


############################