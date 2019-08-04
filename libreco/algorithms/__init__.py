from .user_KNN import userKNN
from .SVD import SVD_tf
from .ALS import ALS_rating, ALS_ranking
from .FM import FmPure, FmFeat
from .superSVD import superSVD
from .NCF import NCF
from .wide_deep import WideDeep, WideDeepCustom, WideDeep_tf
try:
    from .superSVD_cy import superSVD_cy
    from .superSVD_cys import superSVD_cys
except ImportError:
    pass
