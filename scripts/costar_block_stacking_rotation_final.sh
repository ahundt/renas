#!/bin/bash

export PYTHONPATH="$(pwd)"


# Epoch 620: Training controller
#
# ctrl_step=18570  controller_loss=1494.188 ent=31.84 lr=0.0035 |g|=0.0002   acc=0.6875 bl=62.99 mins=5730.29 rw =111.040000916 mse =0.00900602154434
# angle_error=0.216985523701
# mae=0.126344487071
# --------------------------------------------------------------------------------
# [1 4 1 1 1 1 1 4 3 1 3 0]
# [1 2 1 4 2 2 1 1 2 3 1 1]
# val_acc=1.0000
# controller_loss=6322.51025391
# mse=0.00370951113291
# angle_error=0.104434356093
# mae=0.126305446029
# -------------------------
fixed_arc="1 4 1 1 1 1 1 4 3 1 3 0"
fixed_arc="$fixed_arc 1 4 1 1 1 1 1 4 3 1 3 0"

python enas/cifar10/main.py \
  --data_format="NHWC" \
  --search_for="micro" \
  --reset_output_dir \
  --output_dir="2018_09_14_1249_stacking_outputs_rotation_final_with_root_msle" \
  --batch_size=32 \
  --num_epochs=630 \
  --log_every=50 \
  --eval_every_epochs=10 \
  --child_fixed_arc="${fixed_arc}" \
  --child_use_aux_heads \
  --child_num_layers=10 \
  --child_out_filters=36 \
  --child_num_branches=5 \
  --child_num_cells=3 \
  --child_keep_prob=0.80 \
  --child_drop_path_keep_prob=0.60 \
  --child_l2_reg=2e-4 \
  --child_lr_cosine \
  --child_lr_max=1.0 \
  --child_lr_min=0.0001 \
  --child_lr_T_0=10 \
  --child_lr_T_mul=2 \
  --nocontroller_training \
  --controller_search_whole_channels \
  --controller_entropy_weight=0.0001 \
  --controller_train_every=1 \
  --controller_sync_replicas \
  --controller_num_aggregate=10 \
  --controller_train_steps=50 \
  --controller_lr=0.001 \
  --controller_tanh_constant=1.50 \
  --controller_op_tanh_reduce=2.5 \
  --dataset="stacking" \
  --height_img 64 \
  --width_img 64 \
  --rotation_only \
  --max_loss=2 \
  --use_root \
  --use_msle \
  --one_hot_encoding \
  "$@"

