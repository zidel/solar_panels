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


def custom(weights_from, learning_rate):
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

    metrics = [
            'accuracy',
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


def get(model_type, weights_from=None, learning_rate=1e-4):
    if model_type == 'custom':
        return custom(weights_from, learning_rate)
    elif model_type == 'VGG19':
        return vgg19(weights_from, learning_rate)
    elif model_type == 'VGG19_reduced':
        return vgg19_reduced(weights_from, learning_rate)
    elif model_type == 'VGG16':
        return vgg16(weights_from, learning_rate)
    elif model_type == 'MobileNetV2':
        return mobile_v2(weights_from, learning_rate)
    else:
        raise ValueError
