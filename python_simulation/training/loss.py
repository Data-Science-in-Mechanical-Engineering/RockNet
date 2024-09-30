import jax
import jax.numpy as jnp
import equinox as eqx

def cross_entropy(y, pred_y):
    pred_y = jax.nn.log_softmax(pred_y)
    pred_y = pred_y[y]
    return -pred_y

@eqx.filter_jit
def loss_batch(loss, y1, y2):
    return jnp.mean(jax.vmap(loss)(y1, y2))

def accuracy(y, y_pred):
    y_pred = jnp.argmax(y_pred, axis=0)
    return jnp.mean(y == y_pred) * 100

@eqx.filter_jit
def acc_batch(y1, y2):
    return jnp.mean(jax.vmap(accuracy)(y1, y2))

@eqx.filter_jit
def loss_func(model, loss, x, y):
    y_pred = jax.vmap(model)(x)
    loss1 = loss_batch(loss, y, y_pred)

    return loss1

@eqx.filter_jit
def loss_acc_func(model, loss, x, y):
    y_pred = jax.vmap(model)(x)
    return loss_batch(loss, y, y_pred), acc_batch(y, y_pred)

@eqx.filter_jit
def loss_acc_grad_func(model, loss, x, y):
    loss, grad = eqx.filter_value_and_grad(loss_func)(model, loss, x, y)
    y_pred = jax.vmap(model)(x)
    return loss, acc_batch(y, y_pred), grad