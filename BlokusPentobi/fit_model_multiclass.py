import os
import sys
import keras
import tensorflow as tf
import numpy as np
from utils import read_to_dataset
from utils import convert_model_to_tflite
from utils import BlokusPentobiMetric
import argparse

from board_norming import NormalizeBoardToPerspectiveLayer, separate_to_patches


class SaveModelCallback(tf.keras.callbacks.Callback):
    def __init__(self, model_save_path):
        super(SaveModelCallback, self).__init__()
        self.model_save_path = model_save_path

    def on_epoch_end(self, epoch, logs=None):
        self.model.save(self.model_save_path)
        convert_model_to_tflite(self.model_save_path)
        
@tf.keras.saving.register_keras_serializable()     
class TransformerDecoderLayer(tf.keras.layers.Layer):
    """ A Transformer decoder layer.
    Takes in a sequence of vectors, calculates self-attention,
    adds and normalizes, then applies a feed forward layer,
    then adds and normalizes again.
    """
    def __init__(self, num_heads, key_dim, ff_dim, dropout=0.1):
        super(TransformerDecoderLayer, self).__init__()
        self.num_heads = num_heads
        self.key_dim = key_dim
        self.ff_dim = ff_dim
        self.dropout = dropout
        
        self.mha = keras.layers.MultiHeadAttention(num_heads=num_heads, key_dim=key_dim)
        self.ff = keras.Sequential([
            keras.layers.Dense(ff_dim, activation='relu'),
            keras.layers.Dense(key_dim)
        ])
        
        self.layernorm1 = tf.keras.layers.LayerNormalization()
        self.layernorm2 = tf.keras.layers.LayerNormalization()
        
        self.dropout1 = tf.keras.layers.Dropout(dropout)
        self.dropout2 = tf.keras.layers.Dropout(dropout)
        
    def call(self, x):
        attn_output = self.mha(x, x)
        attn_output = self.dropout1(attn_output)
        out1 = self.layernorm1(x + attn_output)
        
        ff_output = self.ff(out1)
        ff_output = self.dropout2(ff_output)
        out2 = self.layernorm2(out1 + ff_output)
        return out2

@tf.keras.saving.register_keras_serializable()     
class DecoderOnlyTransformer(tf.keras.Model):
    """ A plain Decoder only transformer, with no causal masking.
    """
    def __init__(self, num_layers, num_heads, key_dim, ff_dim, dropout=0.1):
        super(DecoderOnlyTransformer, self).__init__()
        self.num_layers = num_layers
        self.num_heads = num_heads
        self.key_dim = key_dim
        self.ff_dim = ff_dim
        self.dropout = dropout
        
        self.decoder_layers = [TransformerDecoderLayer(num_heads, key_dim, ff_dim, dropout) for _ in range(num_layers)]
        
    def call(self, x):
        for i in range(self.num_layers):
            x = self.decoder_layers[i](x)
        return x

def get_model(input_shape, tflite_path=None):
    inputs = keras.Input(shape=input_shape)
    #input_len = input_shape[1]
    
    # Separate the input into the board and the rest
    # Board is everything except the first 2 elements
    board = inputs[:,2:]
    meta = inputs[:,:2]
    
    meta = keras.layers.Flatten()(meta)
    # This element tells whose perspective of the game we are evaluating.
    perspective_pids = meta[:,0]
    perspective_pids = tf.cast(perspective_pids, tf.int32)
    
    # Reshape the board
    board_side_len = int(np.sqrt(board.shape[1]))
    board = tf.reshape(board, (-1, board_side_len, board_side_len))
    
    board = NormalizeBoardToPerspectiveLayer()([board, perspective_pids])
    
    board = tf.reshape(board, (-1, board_side_len, board_side_len, 1))
    
    # Convert the board to a tensor with 5 channels, i.e. one-hot encode the values -1...3
    board = board + 1
    
    # Embed each value (0 ... 4) to 16 dimensions
    embedding_dim = 16
    board = tf.keras.layers.Embedding(5, embedding_dim)(board)
    #board = tf.reshape(board, (-1, board_side_len, board_side_len, 16))
    # Convert to a sequence of vectors for the transformer
    board = tf.reshape(board, (-1, board_side_len*board_side_len, embedding_dim))
    # Positional encoding
    positions = tf.range(board_side_len*board_side_len)
    positions = tf.expand_dims(positions, 0) # (1, board_side_len*board_side_len)
    positions = tf.tile(positions, [tf.shape(board)[0], 1]) # (batch_size, board_side_len*board_side_len)
    positions = tf.keras.layers.Embedding(board_side_len*board_side_len, embedding_dim)(positions)
    board = board + positions
    
    x = DecoderOnlyTransformer(num_layers=8, num_heads=8, key_dim=embedding_dim, ff_dim=128)(board)
    x = tf.keras.layers.Flatten()(x)
    
    output = keras.layers.Dense(4, activation='softmax')(x)
    
    model = tf.keras.Model(inputs=inputs, outputs=output)

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.0001),
        loss=tf.keras.losses.CategoricalCrossentropy()
    )
    return model

def residual_block(x, filters, kernel_size=(3,3)):
    y = keras.layers.Conv2D(filters, kernel_size, padding='same', activation='relu')(x)
    y = keras.layers.Conv2D(filters, kernel_size, padding='same')(y)
    y = keras.layers.Add()([x, y])
    y = keras.layers.ReLU()(y)
    return y

def get_model(input_shape, tflite_path=None):
    inputs = keras.Input(shape=input_shape)
    #input_len = input_shape[1]
    
    # Separate the input into the board and the rest
    # Board is everything except the first 2 elements
    board = inputs[:,2:]
    meta = inputs[:,:2]
    
    meta = keras.layers.Flatten()(meta)
    # This element tells whose perspective of the game we are evaluating.
    perspective_pids = meta[:,0]
    perspective_pids = tf.cast(perspective_pids, tf.int32)
    
    # Reshape the board
    board_side_len = int(np.sqrt(board.shape[1]))
    board = tf.reshape(board, (-1, board_side_len, board_side_len))
    
    board = NormalizeBoardToPerspectiveLayer()([board, perspective_pids])
    
    board = tf.reshape(board, (-1, board_side_len, board_side_len, 1))
    
    # Convert the board to a tensor with 5 channels, i.e. one-hot encode the values -1...3
    board = board + 1
    
    # Embed each value (0 ... 4) to 16 dimensions
    board = tf.keras.layers.Embedding(5, 8)(board)
    board = tf.reshape(board, (-1, board_side_len, board_side_len, 8))
    
    x = keras.layers.Conv2D(64, (5,5), padding='same', activation='relu')(board)

    filters = [64,64,64,64]
    kernel_sizes = [(3,3), (3,3), (3,3),(3,3)]
    assert len(filters) == len(kernel_sizes)
    for i in range(len(filters)):
        # x has to have the same number of channels as filters[i]
        if x.shape[-1] != filters[i]:
            x = keras.layers.Conv2D(filters[i], (1,1), padding='same')(x)
        x = residual_block(x, filters[i], kernel_sizes[i])
        x = keras.layers.BatchNormalization()(x)

    # Global average pooling
    x = keras.layers.GlobalAveragePooling2D()(x)
    output = keras.layers.Dense(4, activation='softmax')(x)
    
    model = tf.keras.Model(inputs=inputs, outputs=output)

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.0001),
        loss=tf.keras.losses.CategoricalCrossentropy(label_smoothing=0.0)
    )
    return model
    
def main(data_folder,
         model_save_path,
         load_model_path = None,
         log_dir = "./logs/",
         num_epochs=25,
         patience=5,
         validation_split=0.2,
         batch_size=64,
         divide_y_by=1
         ):
    # Find all folders inside the data_folder
    data_folders = [os.path.join(data_folder, f) for f in os.listdir(data_folder) if os.path.isdir(os.path.join(data_folder, f))]
    data_folders += [data_folder]
    print(data_folders)
    
    if len(tf.config.experimental.list_physical_devices('GPU')) == 1:
        print("Using single GPU")
        strategy = tf.distribute.OneDeviceStrategy(device="/gpu:0")
    elif len(tf.config.experimental.list_physical_devices('GPU')) > 1:
        print("Using multiple GPUs")
        strategy = tf.distribute.MirroredStrategy()
    else:
        print("Using CPU")
        strategy = tf.distribute.OneDeviceStrategy(device="/cpu:0")
    
    with strategy.scope():
        
        train_ds, val_ds, num_files, approx_num_samples = read_to_dataset(data_folders, frac_test_files=validation_split,filter_files_fn=lambda x: x.endswith(".csv"))
        
        if divide_y_by != 1:
            train_ds = train_ds.map(lambda x, y: (x, y/divide_y_by), num_parallel_calls=tf.data.experimental.AUTOTUNE, deterministic=False)
            val_ds = val_ds.map(lambda x, y: (x, y/divide_y_by), num_parallel_calls=tf.data.experimental.AUTOTUNE, deterministic=False)
        
        first_sample = train_ds.take(1).as_numpy_iterator().next()
        input_shape = first_sample[0].shape
        print(f"First sample: {first_sample}")
        #input_shape = (20*20 +2,)
        print(f"Input shape: {input_shape}")
        print(f"Num samples: {approx_num_samples}")
        
        train_ds = train_ds.shuffle(10000).batch(batch_size, num_parallel_calls=tf.data.experimental.AUTOTUNE, deterministic=False, drop_remainder=True)
        val_ds = val_ds.batch(batch_size, num_parallel_calls=tf.data.experimental.AUTOTUNE, deterministic=False, drop_remainder=True)
        
        train_ds = train_ds.prefetch(tf.data.experimental.AUTOTUNE)
        val_ds = val_ds.prefetch(tf.data.experimental.AUTOTUNE)
        
        if load_model_path:
            model = tf.keras.models.load_model(load_model_path,custom_objects={"BlokusPentobiMetric":BlokusPentobiMetric})
        else:
            model = get_model(input_shape, model_save_path.replace(".keras", ".tflite"))
            print(model.summary())
        
        # Compile the model, keeping optimizer and loss, but adding metrics
        metrics = ["accuracy", "categorical_crossentropy",
                   BlokusPentobiMetric(model_save_path.replace(".keras", ".tflite"),num_games=100, num_cpus=25, game_timeout=60)]
        model.compile(optimizer=model.optimizer, loss=model.loss, metrics=metrics)
        
        
        tb_log = tf.keras.callbacks.TensorBoard(log_dir=log_dir, histogram_freq=1)
        early_stop = tf.keras.callbacks.EarlyStopping(monitor='val_loss', patience=patience, restore_best_weights=True)
        save_model_cb = SaveModelCallback(model_save_path)
        model.fit(train_ds, epochs=num_epochs, callbacks=[tb_log, early_stop,save_model_cb], validation_data=val_ds)
    model.save(model_save_path)
    convert_model_to_tflite(model_save_path)
    
    # Run benchmark.py to test the model
    model_tflite_path = model_save_path.replace(".keras", ".tflite")
    os.system(f"python3 BlokusPentobi/benchmark.py --model_path={model_tflite_path} --num_games=200 --num_cpus=25 --game_timeout=60")
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Train a model with given data.')
    parser.add_argument('--data_folder', type=str, required=True,
                        help='Folder containing the data.')
    parser.add_argument('--load_model_path', type=str, help='Path to load a model from.', default=None)
    parser.add_argument('--model_save_path', type=str, required=True, help='Path to save the trained model.')
    parser.add_argument('--log_dir', type=str, required=False, help='Directory for TensorBoard logs.', default="./blokuslogs/")
    parser.add_argument('--num_epochs', type=int, help='Number of epochs to train.', default=25)
    parser.add_argument('--patience', type=int, help='Patience for early stopping.', default=5)
    parser.add_argument('--validation_split', type=float, help='Validation split.', default=0.2)
    parser.add_argument('--batch_size', type=int, help='Batch size.', default=256)
    parser.add_argument('--divide_y_by', type=int, required=False, help='Divide y by this number.', default=1)
    args = parser.parse_args()
    print(args)
    main(data_folder=args.data_folder,
            model_save_path=args.model_save_path,
            load_model_path=args.load_model_path,
            log_dir=args.log_dir,
            num_epochs=args.num_epochs,
            patience=args.patience,
            validation_split=args.validation_split,
            batch_size=args.batch_size,
            divide_y_by=args.divide_y_by)
    exit(0)
    
    
    