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


def vgg19_base(width, weights_from, learning_rate):
    inputs = keras.layers.Input((256, 256, 3))
    processed = tf.keras.applications.vgg19.preprocess_input(inputs)
    vgg19 = keras.applications.vgg19.VGG19(
            include_top=False,
            input_tensor=processed,
            input_shape=(256, 256, 3),
            )
    vgg19.trainable = False

    flatten = keras.layers.Flatten()(vgg19.output)
    dense_1 = keras.layers.Dense(width, activation='relu')(flatten)
    dense_2 = keras.layers.Dense(width, activation='relu')(dense_1)
    dense_3 = keras.layers.Dense(1, activation='sigmoid')(dense_2)

    model = keras.models.Model(inputs=inputs, outputs=dense_3)

    metrics = [
            keras.metrics.Recall(),
            keras.metrics.Precision(),
            ]
    model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=learning_rate),
            loss=keras.losses.BinaryCrossentropy(),
            metrics=metrics)

    if weights_from:
        model.load_weights(weights_from)

    return model


def vgg19(weights_from, learning_rate):
    return vgg19_base(1024, weights_from, learning_rate)


def vgg19_reduced(weights_from, learning_rate):
    return vgg19_base(512, weights_from, learning_rate)


def vgg16(weights_from, learning_rate):
    inputs = keras.layers.Input((256, 256, 3))
    processed = tf.keras.applications.vgg16.preprocess_input(inputs)
    vgg16 = keras.applications.vgg16.VGG16(
            include_top=False,
            input_tensor=processed,
            input_shape=(256, 256, 3),
            )
    vgg16.trainable = False

    flatten = keras.layers.Flatten()(vgg16.output)
    dense_1 = keras.layers.Dense(1024, activation='relu')(flatten)
    dense_2 = keras.layers.Dense(1024, activation='relu')(dense_1)
    dense_3 = keras.layers.Dense(1, activation='sigmoid')(dense_2)

    model = keras.models.Model(inputs=inputs, outputs=dense_3)

    metrics = [
            keras.metrics.Recall(),
            keras.metrics.Precision(),
            ]
    model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=learning_rate),
            loss=keras.losses.BinaryCrossentropy(),
            metrics=metrics)

    if weights_from:
        model.load_weights(weights_from)

    return model


def mobile_v2(weights_from, learning_rate):
    inputs = keras.layers.Input((256, 256, 3))
    processed = tf.keras.applications.mobilenetv2.preprocess_input(inputs)
    mnv2 = keras.applications.mobilenetv2.MobileNetV2(
            include_top=False,
            input_tensor=processed,
            input_shape=(256, 256, 3),
            )
    mnv2.trainable = False

    flatten = keras.layers.Flatten()(mnv2.output)
    dense_1 = keras.layers.Dense(width, activation='relu')(flatten)
    dense_2 = keras.layers.Dense(width, activation='relu')(dense_1)
    dense_3 = keras.layers.Dense(1, activation='sigmoid')(dense_2)

    model = keras.models.Model(inputs=inputs, outputs=dense_3)

    metrics = [
            keras.metrics.Recall(),
            keras.metrics.Precision(),
            ]
    model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=learning_rate),
            loss=keras.losses.BinaryCrossentropy(),
            metrics=metrics)

    if weights_from:
        model.load_weights(weights_from)

    return model
