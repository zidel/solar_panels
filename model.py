import tensorflow as tf
import tensorflow.keras as keras


class BinaryIoU(keras.metrics.MeanIoU):
    def __init__(self):
        super().__init__(2)

    def update_state(self, y_true, y_pred, sample_weight=None):
        return super().update_state(
                tf.round(y_true),
                tf.round(y_pred),
                sample_weight)


def conv_layer(filters, kernel_size):
    return keras.layers.Conv2D(
            filters,
            kernel_size,
            activation='relu',
            padding='same',
            kernel_initializer='he_normal')


def pool(input_layer):
    return keras.layers.MaxPooling2D()(input_layer)


def classify(weights_from=None):
    inputs = keras.layers.Input((256, 256, 3))
    conv_1 = conv_layer(64, 3)(inputs)
    conv_2 = conv_layer(64, 3)(conv_1)
    pool_1 = pool(conv_2)

    conv_3 = conv_layer(128, 3)(pool_1)
    conv_4 = conv_layer(128, 3)(conv_3)
    pool_2 = pool(conv_4)

    conv_5 = conv_layer(256, 3)(pool_2)
    conv_6 = conv_layer(256, 3)(conv_5)
    conv_7 = conv_layer(256, 3)(conv_6)
    conv_8 = conv_layer(256, 3)(conv_7)
    pool_3 = pool(conv_8)

    conv_9 = conv_layer(512, 3)(pool_3)
    conv_10 = conv_layer(512, 3)(conv_9)
    conv_11 = conv_layer(512, 3)(conv_10)
    conv_12 = conv_layer(512, 3)(conv_11)
    pool_4 = pool(conv_12)

    conv_13 = conv_layer(512, 3)(pool_4)
    conv_14 = conv_layer(512, 3)(conv_13)
    conv_15 = conv_layer(512, 3)(conv_14)
    conv_16 = conv_layer(512, 3)(conv_15)
    pool_5 = pool(conv_16)

    flatten = keras.layers.Flatten()(pool_5)

    dense_1 = keras.layers.Dense(1024, activation='relu')(flatten)
    dense_2 = keras.layers.Dense(1024, activation='relu')(dense_1)
    dense_3 = keras.layers.Dense(1, activation='sigmoid')(dense_2)

    model = keras.models.Model(inputs=inputs, outputs=dense_3)

    model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=1e-4),
            loss=keras.losses.BinaryCrossentropy(),
            metrics=['accuracy'])

    if weights_from:
        model.load_weights(weights_from)

    return model
