import numpy as np
import tensorflow as tf
from tensorflow.python.training import moving_averages
import traceback

from enas.common_ops import create_weight
from enas.common_ops import create_bias


def drop_path(x, keep_prob):
  """Drops out a whole example hiddenstate with the specified probability."""

  batch_size = tf.shape(x)[0]
  noise_shape = [batch_size, 1, 1, 1]
  random_tensor = keep_prob
  random_tensor += tf.random_uniform(noise_shape, dtype=tf.float32)
  binary_tensor = tf.floor(random_tensor)
  x = tf.div(x, keep_prob) * binary_tensor

  return x


def conv(x, filter_size, out_filters, stride, name="conv", padding="SAME",
         data_format="NHWC", seed=None):
  """
  Args:
    stride: [h_stride, w_stride].
  """

  if data_format == "NHWC":
    actual_data_format = "channels_last"
  elif data_format == "NCHW":
    actual_data_format = "channels_first"
  else:
    raise NotImplementedError("Unknown data_format {}".format(data_format))
  x = tf.layers.conv2d(
      x, out_filters, [filter_size, filter_size], stride, padding,
      data_format=actual_data_format,
      kernel_initializer=tf.contrib.keras.initializers.he_normal(seed=seed))

  return x


def fully_connected(x, out_size, name="fc", seed=None):
  in_size = x.get_shape()[-1].value
  with tf.variable_scope(name):
    w = create_weight("w", [in_size, out_size], seed=seed)
  x = tf.matmul(x, w)
  return x


def max_pool(x, k_size, stride, padding="SAME", data_format="NHWC",
             keep_size=False):
  """
  Args:
    k_size: two numbers [h_k_size, w_k_size].
    stride: two numbers [h_stride, w_stride].
  """

  if data_format == "NHWC":
    actual_data_format = "channels_last"
  elif data_format == "NCHW":
    actual_data_format = "channels_first"
  else:
    raise NotImplementedError("Unknown data_format {}".format(data_format))
  out = tf.layers.max_pooling2d(x, k_size, stride, padding,
                                data_format=actual_data_format)

  if keep_size:
    if data_format == "NHWC":
      h_pad = (x.get_shape()[1].value - out.get_shape()[1].value) // 2
      w_pad = (x.get_shape()[2].value - out.get_shape()[2].value) // 2
      out = tf.pad(out, [[0, 0], [h_pad, h_pad], [w_pad, w_pad], [0, 0]])
    elif data_format == "NCHW":
      h_pad = (x.get_shape()[2].value - out.get_shape()[2].value) // 2
      w_pad = (x.get_shape()[3].value - out.get_shape()[3].value) // 2
      out = tf.pad(out, [[0, 0], [0, 0], [h_pad, h_pad], [w_pad, w_pad]])
    else:
      raise NotImplementedError("Unknown data_format {}".format(data_format))
  return out


def global_avg_pool(x, data_format="NHWC"):
  if data_format == "NHWC":
    x = tf.reduce_mean(x, [1, 2])
  elif data_format == "NCHW":
    x = tf.reduce_mean(x, [2, 3])
  else:
    raise NotImplementedError("Unknown data_format {}".format(data_format))
  return x


def global_max_pool(x, data_format="NHWC"):
  if data_format == "NHWC":
    x = tf.reduce_max(x, [1, 2])
  elif data_format == "NCHW":
    x = tf.reduce_max(x, [2, 3])
  else:
    raise NotImplementedError("Unknown data_format {}".format(data_format))
  return x


def batch_norm(x, is_training, name="bn", decay=0.9, epsilon=1e-5,
               data_format="NHWC"):
  if data_format == "NHWC":
    shape = [x.get_shape()[3]]
  elif data_format == "NCHW":
    shape = [x.get_shape()[1]]
  else:
    raise NotImplementedError("Unknown data_format {}".format(data_format))

  with tf.variable_scope(name, reuse=None if is_training else True):
    offset = tf.get_variable(
      "offset", shape,
      initializer=tf.constant_initializer(0.0, dtype=tf.float32))
    scale = tf.get_variable(
      "scale", shape,
      initializer=tf.constant_initializer(1.0, dtype=tf.float32))
    moving_mean = tf.get_variable(
      "moving_mean", shape, trainable=False,
      initializer=tf.constant_initializer(0.0, dtype=tf.float32))
    moving_variance = tf.get_variable(
      "moving_variance", shape, trainable=False,
      initializer=tf.constant_initializer(1.0, dtype=tf.float32))

    if is_training:
      x, mean, variance = tf.nn.fused_batch_norm(
        x, scale, offset, epsilon=epsilon, data_format=data_format,
        is_training=True)
      update_mean = moving_averages.assign_moving_average(
        moving_mean, mean, decay)
      update_variance = moving_averages.assign_moving_average(
        moving_variance, variance, decay)
      with tf.control_dependencies([update_mean, update_variance]):
        x = tf.identity(x)
    else:
      x, _, _ = tf.nn.fused_batch_norm(x, scale, offset, mean=moving_mean,
                                       variance=moving_variance,
                                       epsilon=epsilon, data_format=data_format,
                                       is_training=False)
  return x


def norm(x, is_training, name=None, decay=0.9, epsilon=1e-5, data_format="NHWC", norm_type='group', G=32, verbose=0):
  """ Perform batch normalization or group normalization, depending on norm_type argument.
  norm_type: options include, none, batch, and group.
  reference: https://github.com/shaohua0116/Group-Normalization-Tensorflow
  """
  shape_list = x.get_shape().as_list()
  if verbose > 0:
    print('-' * 80)
    print('group_norm input x shape outside scope: ' + str(shape_list) + ' data_format: ' + str(data_format))
    for line in traceback.format_stack():
        print(line.strip())
  if data_format == "NHWC":
    c_shape = [x.get_shape()[3]]
  elif data_format == "NCHW":
    c_shape = [x.get_shape()[1]]
  else:
    raise NotImplementedError("Unknown data_format {}".format(data_format))
  if name is None:
      name = norm_type + '_norm'
  with tf.variable_scope(name, reuse=None if is_training else True):

    if norm_type == 'none':
      output = x
    elif norm_type == 'batch':
      output = batch_norm(
        x=x, is_training=is_training, name=name,
        decay=decay, epsilon=epsilon, data_format=data_format)
    elif norm_type == 'group':
      # normalize
      # tranpose: [bs, h, w, c] to [bs, c, h, w] following the paper
      # print('group_norm input x shape inside scope: ' + str(x.get_shape().as_list()))
      if data_format == "NHWC":
          x = tf.transpose(x, [0, 3, 1, 2])
          # c_shape = [x.get_shape()[3]]
          # channels_axis=-1, reduction_axes=[-3, -2]
      elif data_format == "NCHW":
          pass
          # already in the right format
          # c_shape = [x.get_shape()[1]]
          # channels_axis=-3, reduction_axes=[-2, -1]
      else:
        raise NotImplementedError("Unknown data_format {}".format(data_format))
      shape = tf.shape(x)
      N = shape[0]
      C = shape[1]
      H = shape[2]
      W = shape[3]
      G = tf.minimum(G, C)
      x = tf.reshape(x, [N, G, C // G, H, W])
      mean, var = tf.nn.moments(x, [2, 3, 4], keep_dims=True)
      x = (x - mean) / tf.sqrt(var + epsilon)
      # per channel gamma and beta
      gamma = tf.get_variable('gamma', c_shape,
                              initializer=tf.constant_initializer(1.0, dtype=tf.float32))
      beta = tf.get_variable('beta', c_shape,
                             initializer=tf.constant_initializer(0.0, dtype=tf.float32))
      gamma = tf.reshape(gamma, [1, C, 1, 1])
      beta = tf.reshape(beta, [1, C, 1, 1])

      output = tf.reshape(x, [N, C, H, W]) * gamma + beta

      if data_format == "NHWC":
          # tranpose: [bs, c, h, w, c] to [bs, h, w, c] following the paper
          output = tf.transpose(output, [0, 2, 3, 1])
      elif data_format == "NCHW":
          # already in the right format
          pass
      else:
        raise NotImplementedError("Unknown data_format {}".format(data_format))
      # recover initial shape information
      if shape_list[0] is None:
        # first index is batch, that should be inferred
        shape_list[0] = -1
      output = tf.reshape(output, shape_list)
    else:
        raise NotImplementedError
  return output


def batch_norm_with_mask(x, is_training, mask, num_channels, name="bn",
                         decay=0.9, epsilon=1e-3, data_format="NHWC"):

  shape = [num_channels]
  indices = tf.where(mask)
  indices = tf.to_int32(indices)
  indices = tf.reshape(indices, [-1])

  with tf.variable_scope(name, reuse=None if is_training else True):
    offset = tf.get_variable(
      "offset", shape,
      initializer=tf.constant_initializer(0.0, dtype=tf.float32))
    scale = tf.get_variable(
      "scale", shape,
      initializer=tf.constant_initializer(1.0, dtype=tf.float32))
    offset = tf.boolean_mask(offset, mask)
    scale = tf.boolean_mask(scale, mask)

    moving_mean = tf.get_variable(
      "moving_mean", shape, trainable=False,
      initializer=tf.constant_initializer(0.0, dtype=tf.float32))
    moving_variance = tf.get_variable(
      "moving_variance", shape, trainable=False,
      initializer=tf.constant_initializer(1.0, dtype=tf.float32))

    if is_training:
      x, mean, variance = tf.nn.fused_batch_norm(
        x, scale, offset, epsilon=epsilon, data_format=data_format,
        is_training=True)
      mean = (1.0 - decay) * (tf.boolean_mask(moving_mean, mask) - mean)
      variance = (1.0 - decay) * (tf.boolean_mask(moving_variance, mask) - variance)
      update_mean = tf.scatter_sub(moving_mean, indices, mean, use_locking=True)
      update_variance = tf.scatter_sub(
        moving_variance, indices, variance, use_locking=True)
      with tf.control_dependencies([update_mean, update_variance]):
        x = tf.identity(x)
    else:
      masked_moving_mean = tf.boolean_mask(moving_mean, mask)
      masked_moving_variance = tf.boolean_mask(moving_variance, mask)
      x, _, _ = tf.nn.fused_batch_norm(x, scale, offset,
                                       mean=masked_moving_mean,
                                       variance=masked_moving_variance,
                                       epsilon=epsilon, data_format=data_format,
                                       is_training=False)
  return x


def relu(x, leaky=0.0):
  return tf.where(tf.greater(x, 0), x, x * leaky)
