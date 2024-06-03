
import os
import random
from typing import List

import numpy as np
import tensorflow as tf


def read_to_dataset(paths,
                    frac_test_files=0,
                    add_channel=False,
                    shuffle_files=True,
                    filter_files_fn = None):
    """ Create a tf dataset from a folder of files.
    If split_files_to_test_set is True, then frac_test_files of the files are used for testing.
    
    """
    assert 0 <= frac_test_files <= 1, "frac_test_files must be between 0 and 1"
    if not isinstance(paths, (list, tuple)):
        paths = [paths]
    if filter_files_fn is None:
        filter_files_fn = lambda x: True
    
    # Find all files in paths, that fit the filter_files_fn
    file_paths = [os.path.join(path, file) for path in paths for file in os.listdir(path) if filter_files_fn(file)]
    if shuffle_files:
        random.shuffle(file_paths)
        
    # Read one file to get the number of samples in a file
    with open(file_paths[0], "r") as f:
        num_samples = sum(1 for line in f)

    print("Found {} files".format(len(file_paths)))
    def txt_line_to_tensor(x):
        s = tf.strings.split(x, sep=",")
        s = tf.strings.to_number(s, out_type=tf.float32)
        return (s[:-1], s[-1])

    def ds_maker(x):
        ds = tf.data.TextLineDataset(x, num_parallel_reads=tf.data.experimental.AUTOTUNE)
        ds = ds.map(txt_line_to_tensor,
                    num_parallel_calls=tf.data.experimental.AUTOTUNE,
                    deterministic=False)
        return ds
    
    test_files = file_paths[:int(frac_test_files*len(file_paths))]
    train_files = file_paths[int(frac_test_files*len(file_paths)):]
    
    if len(test_files) > 0:
        test_ds = tf.data.Dataset.from_tensor_slices(test_files)
        test_ds = test_ds.interleave(ds_maker,
                                cycle_length=tf.data.experimental.AUTOTUNE,
                                num_parallel_calls=tf.data.experimental.AUTOTUNE,
                                deterministic=False)
        if add_channel:
            test_ds = test_ds.map(lambda x, y: (tf.expand_dims(x, axis=-1), y), num_parallel_calls=tf.data.experimental.AUTOTUNE)
    train_ds = tf.data.Dataset.from_tensor_slices(train_files)
    train_ds = train_ds.interleave(ds_maker,
                                cycle_length=tf.data.experimental.AUTOTUNE,
                                num_parallel_calls=tf.data.experimental.AUTOTUNE,
                                deterministic=False)
    # Add a channel dimension if necessary
    if add_channel:
        train_ds = train_ds.map(lambda x, y: (tf.expand_dims(x, axis=-1), y), num_parallel_calls=tf.data.experimental.AUTOTUNE)
    if len(test_files) > 0:
        return train_ds, test_ds, len(file_paths), num_samples*len(file_paths)
    return train_ds, len(file_paths), num_samples*len(file_paths)

class TFLiteModel:
    """ A class representing a tensorflow lite model.
    """
    def __init__(self, path : str, expand_input_dims : bool = False):
        """ Initialize the model.
        """
        path = os.path.abspath(path)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Model file not found at {path}")
        self.interpreter = tf.lite.Interpreter(model_path=path)
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        self.interpreter.allocate_tensors()
        
    def is_valid_size_input(self, X) -> bool:
        """ Validate the input.
        """
        is_valid = X.shape[1:] == self.input_details[0]['shape'][1:]
        return True if all(is_valid) else False
        
    def predict(self, X) -> List[float]:
        """ Predict the output of the model.
        The input should be a numpy array with size (batch_size, input_size)
        """
        if not self.is_valid_size_input(X):
            # Add a dimension to the input
            X = np.expand_dims(X, axis = -1)
            if not self.is_valid_size_input(X):
                raise ValueError(f"Input shape {X.shape} is not valid for the model. Expected shape {self.input_details[0]['shape']}")
        self.interpreter.resize_tensor_input(self.input_details[0]['index'], X.shape)
        self.interpreter.allocate_tensors()
        self.interpreter.set_tensor(self.input_details[0]['index'], X)
        self.interpreter.invoke()
        out = self.interpreter.get_tensor(self.output_details[0]['index'])
        return list(out)
    

def convert_model_to_tflite(file_path : str, output_file : str = None) -> None:
    if output_file is None:
        output_file = file_path.replace(".keras", ".tflite")
        
    print("Converting '{}' to '{}'".format(file_path, output_file))

    model = tf.keras.models.load_model(file_path)
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.target_spec.supported_ops = [
        tf.lite.OpsSet.TFLITE_BUILTINS, # enable TensorFlow Lite ops.
        tf.lite.OpsSet.SELECT_TF_OPS # enable TensorFlow ops.
    ]
    tflite_model = converter.convert()

    with open(output_file, "wb") as f:
        f.write(tflite_model)
    return output_file