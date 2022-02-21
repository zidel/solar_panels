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
    processed = tf.keras.applications.mobilenet_v2.preprocess_input(inputs)
    mnv2 = keras.applications.mobilenet_v2.MobileNetV2(
            include_top=False,
            input_tensor=processed,
            input_shape=(256, 256, 3),
            )
    mnv2.trainable = False

    flatten = keras.layers.Flatten()(mnv2.output)
    dense_1 = keras.layers.Dense(1024, activation='relu')(flatten)
    dense_2 = keras.layers.Dense(1, activation='sigmoid')(dense_1)

    model = keras.models.Model(inputs=inputs, outputs=dense_2)

    metrics = [
            keras.metrics.Recall(),
            keras.metrics.Precision(),
            ]
    model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=1e-6),
            loss=keras.losses.BinaryCrossentropy(),
            metrics=metrics)

    if weights_from:
        model.load_weights(weights_from)

    return model
