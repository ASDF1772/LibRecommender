"""

Reference: Xiangnan He et al. "Neural Collaborative Filtering"
           (https://arxiv.org/pdf/1708.05031.pdf)

author: massquantity

"""
from tensorflow.keras.initializers import glorot_uniform

from ..bases import ModelMeta, TfBase
from ..prediction import normalize_prediction
from ..tfops import dense_nn, dropout_config, reg_config, tf, tf_dense
from ..torchops import hidden_units_config
from ..utils.validate import check_unknown, convert_id


class NCF(TfBase, metaclass=ModelMeta):
    user_variables = ["user_gmf", "user_mlp"]
    item_variables = ["item_gmf", "item_mlp"]

    def __init__(
        self,
        task,
        data_info,
        loss_type="cross_entropy",
        embed_size=16,
        n_epochs=20,
        lr=0.01,
        lr_decay=False,
        epsilon=1e-5,
        reg=None,
        batch_size=256,
        num_neg=1,
        use_bn=True,
        dropout_rate=None,
        hidden_units=(128, 64, 32),
        seed=42,
        lower_upper_bound=None,
        tf_sess_config=None,
    ):
        super().__init__(task, data_info, lower_upper_bound, tf_sess_config)

        self.all_args = locals()
        self.loss_type = loss_type
        self.embed_size = embed_size
        self.n_epochs = n_epochs
        self.lr = lr
        self.lr_decay = lr_decay
        self.epsilon = epsilon
        self.reg = reg_config(reg)
        self.batch_size = batch_size
        self.num_neg = num_neg
        self.use_bn = use_bn
        self.dropout_rate = dropout_config(dropout_rate)
        self.hidden_units = hidden_units_config(hidden_units)
        self.seed = seed

    def build_model(self):
        self.user_indices = tf.placeholder(tf.int32, shape=[None])
        self.item_indices = tf.placeholder(tf.int32, shape=[None])
        self.labels = tf.placeholder(tf.float32, shape=[None])
        self.is_training = tf.placeholder_with_default(False, shape=[])

        user_gmf = tf.get_variable(
            name="user_gmf",
            shape=[self.n_users + 1, self.embed_size],
            initializer=glorot_uniform,
            regularizer=self.reg,
        )
        item_gmf = tf.get_variable(
            name="item_gmf",
            shape=[self.n_items + 1, self.embed_size],
            initializer=glorot_uniform,
            regularizer=self.reg,
        )
        user_mlp = tf.get_variable(
            name="user_mlp",
            shape=[self.n_users + 1, self.embed_size],
            initializer=glorot_uniform,
            regularizer=self.reg,
        )
        item_mlp = tf.get_variable(
            name="item_mlp",
            shape=[self.n_items + 1, self.embed_size],
            initializer=glorot_uniform,
            regularizer=self.reg,
        )

        user_gmf_embed = tf.nn.embedding_lookup(user_gmf, self.user_indices)
        item_gmf_embed = tf.nn.embedding_lookup(item_gmf, self.item_indices)
        user_mlp_embed = tf.nn.embedding_lookup(user_mlp, self.user_indices)
        item_mlp_embed = tf.nn.embedding_lookup(item_mlp, self.item_indices)

        gmf_layer = tf.multiply(user_gmf_embed, item_gmf_embed)
        mlp_input = tf.concat([user_mlp_embed, item_mlp_embed], axis=1)
        mlp_layer = dense_nn(
            mlp_input,
            self.hidden_units,
            use_bn=self.use_bn,
            dropout_rate=self.dropout_rate,
            is_training=self.is_training,
        )
        concat_layer = tf.concat([gmf_layer, mlp_layer], axis=1)
        self.output = tf.reshape(tf_dense(units=1)(concat_layer), [-1])

    def predict(self, user, item, feats=None, cold_start="average", inner_id=False):
        assert feats is None, "NCF can't use features."
        user, item = convert_id(self, user, item, inner_id)
        unknown_num, unknown_index, user, item = check_unknown(self, user, item)
        preds = self.sess.run(
            self.output,
            feed_dict={
                self.user_indices: user,
                self.item_indices: item,
                self.is_training: False,
            },
        )
        return normalize_prediction(preds, self, cold_start, unknown_num, unknown_index)

    def recommend_user(
        self,
        user,
        n_rec,
        user_feats=None,
        item_data=None,
        cold_start="average",
        inner_id=False,
        filter_consumed=True,
        random_rec=False,
    ):
        assert user_feats is None and item_data is None, "NCF can't use features."
        return super().recommend_user(
            user,
            n_rec,
            user_feats,
            item_data,
            cold_start,
            inner_id,
            filter_consumed,
            random_rec,
        )
