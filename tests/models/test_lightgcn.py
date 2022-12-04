import pytest
import tensorflow as tf

from libreco.algorithms import LightGCN

from tests.utils_metrics import get_metrics
from tests.utils_path import remove_path
from tests.utils_pred import ptest_preds
from tests.utils_reco import ptest_recommends
from tests.utils_save_load import save_load_model


@pytest.mark.parametrize("task", ["rating", "ranking"])
@pytest.mark.parametrize(
    "loss_type, sampler, num_neg",
    [
        ("cross_entropy", "random", 1),
        ("cross_entropy", "random", 0),
        ("focal", None, 1),
        ("focal", "unconsumed", 3),
        ("bpr", "popular", 3),
        ("max_margin", "random", 2),
        ("max_margin", None, 2),
        ("whatever", "random", 1),
        ("bpr", "whatever", 1),
    ],
)
@pytest.mark.parametrize(
    "reg, dropout, lr_decay, epsilon, amsgrad",
    [(0.0, 0.0, False, 1e-8, False), (0.01, 0.2, True, 4e-5, True)],
)
def test_lightgcn(
    prepare_pure_data,
    task,
    loss_type,
    sampler,
    num_neg,
    reg,
    dropout,
    lr_decay,
    epsilon,
    amsgrad,
):
    tf.compat.v1.reset_default_graph()
    pd_data, train_data, eval_data, data_info = prepare_pure_data
    if task == "ranking":
        # train_data.build_negative_samples(data_info, seed=2022)
        eval_data.build_negative_samples(data_info, seed=2222)

    if task == "rating":
        with pytest.raises(ValueError):
            _ = LightGCN(task, data_info)
    elif loss_type == "whatever":
        with pytest.raises(ValueError):
            _ = LightGCN(task, data_info, loss_type, sampler=sampler, num_neg=num_neg)
    elif loss_type == "cross_entropy" and sampler and num_neg <= 0:
        with pytest.raises(AssertionError):
            _ = LightGCN(task, data_info, loss_type, sampler=sampler, num_neg=num_neg)
    elif loss_type == "max_margin" and not sampler:
        with pytest.raises(ValueError):
            _ = LightGCN(task, data_info, loss_type, sampler=sampler, num_neg=num_neg)
    elif sampler and sampler == "whatever":
        with pytest.raises(ValueError):
            _ = LightGCN(task, data_info, loss_type, sampler=sampler, num_neg=num_neg)
    else:
        model = LightGCN(
            task=task,
            data_info=data_info,
            loss_type=loss_type,
            embed_size=16,
            n_epochs=1,
            lr=1e-4,
            lr_decay=lr_decay,
            epsilon=epsilon,
            amsgrad=amsgrad,
            batch_size=1024,
            n_layers=3,
            reg=reg,
            dropout=dropout,
            num_neg=num_neg,
            sampler=sampler,
        )
        model.fit(
            train_data,
            verbose=2,
            shuffle=True,
            eval_data=eval_data,
            metrics=get_metrics(task),
        )
        ptest_preds(model, task, pd_data, with_feats=False)
        ptest_recommends(model, data_info, pd_data, with_feats=False)

        # test save and load model
        loaded_model, loaded_data_info = save_load_model(LightGCN, model, data_info)
        ptest_preds(loaded_model, task, pd_data, with_feats=False)
        ptest_recommends(loaded_model, loaded_data_info, pd_data, with_feats=False)
        model.save("not_existed_path", "lightgcn2")
        remove_path("not_existed_path")
