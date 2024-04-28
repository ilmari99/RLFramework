import os
import tensorflow as tf
import numpy as np
from RLFramework.read_to_dataset import read_to_dataset
from RLFramework.utils import convert_model_to_tflite
import argparse

def get_conv_model(input_shape):
    inputs = tf.keras.Input(shape=input_shape)
    
    # First separate the input into misc and card data:
    # The first 15 values are miscellanous
    misc = tf.gather(inputs, [i for i in range(15)], axis=1)
    # The rest are card data
    cards = tf.gather(inputs, [i for i in range(15, input_shape[0])], axis=1)
    # We then reshape the card data to 8x52x1
    # 8 players, 52 cards (1 means the card is in the set, 0 means it is not), 1 channel
    cards = tf.keras.layers.Reshape((8,52,1))(cards)
    # And apply convolutional layers
    x = tf.keras.layers.Conv2D(16, (3,3), activation='relu')(cards)
    x = tf.keras.layers.Conv2D(32, (3,3), activation='relu')(x)
    x = tf.keras.layers.Conv2D(64, (3,3), activation='relu')(x)
    x = tf.keras.layers.Flatten()(x)
    # Concatenate the misc data to the convolutional layers
    x = tf.keras.layers.Concatenate()([x, misc])
    # And apply dense layers
    x = tf.keras.layers.Dense(128, activation='relu')(x)
    x = tf.keras.layers.Dropout(0.5)(x)
    x = tf.keras.layers.Dense(64, activation='relu')(x)
    x = tf.keras.layers.Dropout(0.5)(x)
    x = tf.keras.layers.Dense(1, activation='sigmoid')(x)
    model = tf.keras.Model(inputs=inputs, outputs=x)
    model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy', "mae"])
    return model

def get_mlp_model(input_shape):
    inputs = tf.keras.Input(shape=input_shape)
    x = tf.keras.layers.Dense(600, activation='relu')(inputs)
    x = tf.keras.layers.Dropout(0.4)(x)
    x = tf.keras.layers.Dense(500, activation='relu')(x)
    x = tf.keras.layers.Dropout(0.35)(x)
    x = tf.keras.layers.Dense(500, activation='relu')(x)
    x = tf.keras.layers.Dropout(0.35)(x)
    x = tf.keras.layers.Dense(500, activation='relu')(x)
    output = tf.keras.layers.Dense(1, activation='sigmoid')(x)
    
    model = tf.keras.Model(inputs=inputs, outputs=output)

    model.compile(optimizer="adam",
            loss='binary_crossentropy',
            metrics=['mae', "accuracy"]
    )
    return model

class SaveModelCallback(tf.keras.callbacks.Callback):
    def __init__(self, model_save_path):
        super(SaveModelCallback, self).__init__()
        self.model_save_path = model_save_path

    def on_epoch_end(self, epoch, logs=None):
        self.model.save(self.model_save_path)
        convert_model_to_tflite(self.model_save_path)
    
def main(data_folder,
         model_save_path,
         load_model_path = None,
         log_dir = "./logs/",
         num_epochs=25,
         patience=5,
         validation_split=0.2,
         batch_size=64,
         model_type="conv",
         ):
    data_folders = [os.path.join(data_folder, f) for f in os.listdir(data_folder) if os.path.isdir(os.path.join(data_folder, f))]
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
        train_ds, val_ds, num_files, approx_num_samples = read_to_dataset(data_folders, frac_test_files=validation_split)
        
        input_shape = train_ds.take(1).as_numpy_iterator().next()[0].shape
        print(f"Input shape: {input_shape}")
        print(f"Num samples: {approx_num_samples}")
        
        train_ds = train_ds.batch(batch_size)
        val_ds = val_ds.batch(batch_size)
        
        train_ds = train_ds.prefetch(tf.data.experimental.AUTOTUNE)
        val_ds = val_ds.prefetch(tf.data.experimental.AUTOTUNE)
        
        if load_model_path:
            model = tf.keras.models.load_model(load_model_path)
        else:
            if model_type == "mlp":
                model = get_mlp_model(input_shape)
            else:
                model = get_conv_model(input_shape)
            print(model.summary())
        
        tb_log = tf.keras.callbacks.TensorBoard(log_dir=log_dir, histogram_freq=1)
        early_stop = tf.keras.callbacks.EarlyStopping(monitor='val_loss', patience=patience, restore_best_weights=True)
        save_model_cb = SaveModelCallback(model_save_path)
        model.fit(train_ds, epochs=num_epochs, callbacks=[tb_log, early_stop, save_model_cb], validation_data=val_ds,class_weight={0: 0.75, 1: 0.25})
    model.save(model_save_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Train a model with given data.')
    parser.add_argument('--data_folder', type=str, required=True,
                        help='Folders containing the data. Provide as a space separated list.')
    parser.add_argument('--load_model_path', type=str, help='Path to load a model from.', default=None)
    parser.add_argument('--model_save_path', type=str, required=True, help='Path to save the trained model.')
    parser.add_argument('--log_dir', type=str, required=False, help='Directory for TensorBoard logs.', default="./moskalogs/")
    parser.add_argument('--num_epochs', type=int, help='Number of epochs to train.', default=25)
    parser.add_argument('--patience', type=int, help='Patience for early stopping.', default=5)
    parser.add_argument('--validation_split', type=float, help='Validation split.', default=0.2)
    parser.add_argument('--batch_size', type=int, help='Batch size.', default=64)
    parser.add_argument('--model_type', type=str, help='Type of model to use (mlp or conv).', default="conv")
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
            model_type=args.model_type,
            )
    convert_model_to_tflite(args.model_save_path)
    exit(0)
    
    
    