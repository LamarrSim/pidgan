import os

import pytest
import keras as k
import tensorflow as tf

CHUNK_SIZE = int(1e4)
BATCH_SIZE = 500

here = os.path.dirname(__file__)
export_dir = f"{here}/tmp/aux-discriminator"

x = tf.random.normal(shape=(CHUNK_SIZE, 4))
y = tf.random.normal(shape=(CHUNK_SIZE, 8))
w = tf.random.uniform(shape=(CHUNK_SIZE,))
labels = tf.random.uniform(shape=(CHUNK_SIZE,), minval=0.0, maxval=1.0)
labels = tf.cast(labels > 0.5, x.dtype)


@pytest.fixture
def model():
    from pidgan.players.discriminators import AuxDiscriminator

    disc = AuxDiscriminator(
        output_dim=1,
        aux_features=["0 + 1", "2 - 3", "4 * 5", "6 / 7"],
        num_hidden_layers=5,
        mlp_hidden_units=128,
        mlp_dropout_rates=0.0,
        enable_residual_blocks=False,
        output_activation="sigmoid",
    )
    disc.build(input_shape=(x.shape, y.shape))
    return disc


###########################################################################


def test_model_configuration(model):
    from pidgan.players.discriminators import AuxDiscriminator

    assert isinstance(model, AuxDiscriminator)
    assert isinstance(model.output_dim, int)
    assert isinstance(model.aux_features, list)
    assert isinstance(model.num_hidden_layers, int)
    assert isinstance(model.mlp_hidden_units, int)
    assert isinstance(model.mlp_dropout_rates, float)
    assert isinstance(model.enable_residual_blocks, bool)
    # assert isinstance(model.output_activation, str)


@pytest.mark.parametrize("enable_res_blocks", [True, False])
@pytest.mark.parametrize("output_activation", ["sigmoid", None])
def test_model_use(enable_res_blocks, output_activation):
    from pidgan.players.discriminators import AuxDiscriminator

    model = AuxDiscriminator(
        output_dim=1,
        aux_features=["0 + 1", "2 - 3", "4 * 5", "6 / 7"],
        num_hidden_layers=3,
        mlp_hidden_units=128,
        mlp_dropout_rates=0.0,
        enable_residual_blocks=enable_res_blocks,
        output_activation=output_activation,
    )
    model.build(input_shape=(x.shape, y.shape))

    out = model((x, y))
    model.summary()
    test_shape = [x.shape[0]]
    test_shape.append(model.output_dim)
    assert out.shape == tuple(test_shape)
    hidden_feat = model.hidden_feature((x, y))
    test_shape = [x.shape[0]]
    test_shape.append(model.mlp_hidden_units)
    assert hidden_feat.shape == tuple(test_shape)
    assert isinstance(model.export_model, k.Model)


@pytest.mark.parametrize("sample_weight", [w, None])
def test_model_train(model, sample_weight):
    if sample_weight is not None:
        slices = ((x, y), labels, w)
    else:
        slices = ((x, y), labels)
    dataset = (
        tf.data.Dataset.from_tensor_slices(slices)
        .batch(batch_size=BATCH_SIZE, drop_remainder=True)
        .cache()
        .prefetch(tf.data.AUTOTUNE)
    )
    model.compile(
        optimizer=k.optimizers.Adam(learning_rate=0.001),
        loss=k.losses.MeanSquaredError(),
        metrics=["mae"],
    )
    model.fit(dataset, epochs=2)


@pytest.mark.parametrize("sample_weight", [w, None])
def test_model_eval(model, sample_weight):
    model.compile(
        optimizer=k.optimizers.Adam(learning_rate=0.001),
        loss=k.losses.MeanSquaredError(),
        metrics=["mae"],
    )
    model.evaluate(x=(x, y), y=labels, sample_weight=sample_weight)


def test_model_export(model):
    out, aux = model((x, y), return_aux_features=True)

    v_major, v_minor, _ = [int(v) for v in k.__version__.split(".")]
    if v_major == 3 and v_minor >= 0:
        model.export_model.export(export_dir)
        model_reloaded = k.layers.TFSMLayer(export_dir, call_endpoint="serve")
    else:
        k.models.save_model(model.export_model, export_dir, save_format="tf")
        model_reloaded = k.models.load_model(export_dir)

    in_reloaded = tf.concat((x, y, aux), axis=-1)
    out_reloaded = model_reloaded(in_reloaded)
    comparison = out.numpy() == out_reloaded.numpy()
    assert comparison.all()
