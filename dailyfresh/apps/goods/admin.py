from django.contrib import admin
from django.core.cache import cache
from apps.goods.models import GoodsType, GoodsSKU, Goods, GoodsImage,IndexGoodsBanner,IndexTypeGoodsBanner,IndexPromotionBanner
# Register your models here.

# 网站优化　　　１．生成静态页面　　　２．生成缓存
# 生成静态页面
class BaseAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        from celery_tasks.tasks import generate_static_html
        generate_static_html.delay()
        # 删除缓存
        cache.delete('static_html_cache')
        # print("-----666-------")

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        from celery_tasks.tasks import generate_static_html
        generate_static_html.delay()
        # 删除缓存
        cache.delete('static_html_cache')


class IndexGoodsBannerAdmin(BaseAdmin):
    pass

class IndexTypeGoodsBannerAdmin(BaseAdmin):
    pass

class IndexPromotionBannerAdmin(BaseAdmin):
    pass

class GoodsTypeAdmin(BaseAdmin):
    pass


admin.site.register(GoodsType, GoodsTypeAdmin)
admin.site.register(GoodsSKU)
admin.site.register(Goods)
admin.site.register(GoodsImage)
admin.site.register(IndexPromotionBanner, IndexPromotionBannerAdmin)
admin.site.register(IndexTypeGoodsBanner, IndexTypeGoodsBannerAdmin)
admin.site.register(IndexGoodsBanner, IndexGoodsBannerAdmin)


