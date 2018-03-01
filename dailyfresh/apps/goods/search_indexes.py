from haystack import indexes
# 导入模型类
from apps.goods.models import GoodsSKU
#指定对于某个类的某些数据建立索引，模型类名＋Ｉｎｄｅｘ
class GoodsSKUIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)

    def get_model(self):
        # 返回模型类
        return GoodsSKU

    def index_queryset(self, using=None):
        return self.get_model().objects.all()