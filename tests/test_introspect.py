import pytest

from django_mermaid_erd import build_schema
from django_mermaid_erd.select import select_models


@pytest.fixture(scope="module")
def schema():
    return build_schema(select_models())


def rels(schema, kind):
    return {(r.source, r.target, r.label) for r in schema.relations if r.kind == kind}


def attrs(schema, key):
    return {a.name: a for a in schema.entity(key).attributes}


def test_entities_sorted_and_builtin_excluded(schema):
    labels = [e.label for e in schema.entities]
    assert labels == sorted(labels, key=lambda label: tuple(label.split(".")))
    assert not any(label.startswith(("auth.", "contenttypes.")) for label in labels)
    assert "inventory.BaseAsset" not in labels  # abstract
    assert len(labels) == 18
    assert schema.apps == ["blog", "inventory", "shop"]


def test_fk(schema):
    assert ("Order", "Customer", "customer") in rels(schema, "fk")
    a = attrs(schema, "Order")["customer"]
    assert a.fk and a.attname == "customer_id" and a.type == "int" and not a.nullable
    assert a.references == "shop.Customer"


def test_nullable_fk(schema):
    rel = next(r for r in schema.relations if r.label == "coupon")
    assert rel.kind == "fk" and rel.nullable
    assert attrs(schema, "Order")["coupon"].nullable


def test_self_reference(schema):
    rel = next(r for r in schema.relations if r.label == "parent")
    assert rel.source == rel.target == "Category" and rel.self_ref and rel.nullable


def test_one_to_one(schema):
    assert ("Stock", "Item", "item") in rels(schema, "o2o")
    a = attrs(schema, "Stock")["item"]
    assert a.fk and a.unique and a.type == "uuid"  # type of the target pk


def test_m2m_auto_through(schema):
    assert ("Order", "Coupon", "coupons") in rels(schema, "m2m")
    assert ("Post", "blog_Tag", "tags") in rels(schema, "m2m")
    assert "coupons" not in attrs(schema, "Order")


def test_m2m_custom_through_in_scope_is_not_drawn(schema):
    m2m = rels(schema, "m2m")
    assert ("Product", "shop_Tag", "tags") not in m2m
    assert ("Warehouse", "Item", "items") not in m2m
    assert ("ProductTag", "shop_Tag", "tag") in rels(schema, "fk")


def test_m2m_custom_through_out_of_scope_is_drawn_with_via():
    schema = build_schema(select_models(exclude=["shop.ProductTag"]))
    rel = next(r for r in schema.relations if r.kind == "m2m" and r.label == "tags" and r.source == "Product")
    assert rel.through == "shop.ProductTag"


def test_mti(schema):
    assert ("Device", "Vehicle", "inherits") in rels(schema, "inherit")
    device = attrs(schema, "Device")
    assert "vehicle_ptr" not in device
    assert set(device) == {"ip_address", "firmware"}  # parent fields not repeated
    assert schema.entity("Device").parents == ["Vehicle"]


def test_abstract_fields_inherited(schema):
    assert list(attrs(schema, "Vehicle")) == ["id", "serial", "purchased_on", "plate"]


def test_proxy(schema):
    assert ("PublishedPost", "Post", "proxy") in rels(schema, "proxy")
    entity = schema.entity("PublishedPost")
    assert entity.proxy and entity.attributes == [] and entity.parents == ["Post"]


def test_no_proxy():
    labels = [e.label for e in build_schema(select_models(include_proxy=False)).entities]
    assert "blog.PublishedPost" not in labels


def test_generic_fk(schema):
    names = list(attrs(schema, "Comment"))
    assert names == ["id", "content_type", "object_id", "content_object", "text"]
    gfk = attrs(schema, "Comment")["content_object"]
    assert gfk.type == "generic" and gfk.comment == "GenericForeignKey"
    assert not rels(schema, "generic")


def test_generic_edges_need_contenttypes_in_scope():
    assert not rels(build_schema(select_models(), generic_edges=True), "generic")
    schema = build_schema(select_models(include_builtin=True), generic_edges=True)
    assert ("Comment", "ContentType", "content_object") in rels(schema, "generic")


def test_uuid_pk_and_types(schema):
    item = attrs(schema, "Item")
    assert item["id"].pk and item["id"].type == "uuid"
    assert (item["attributes"].type, item["thumbnail"].type, item["description"].type) == ("json", "binary", "text")
    assert attrs(schema, "Device")["ip_address"].type == "ip"
    assert attrs(schema, "Device")["firmware"].type == "file"
    assert attrs(schema, "Product")["price"].type_params == "10,2"
    assert attrs(schema, "Product")["name"].type_params == "200"


def test_unmanaged(schema):
    entity = schema.entity("LegacyTable")
    assert not entity.managed
    assert attrs(schema, "LegacyTable")["code"].pk


def test_same_name_models_get_app_prefix(schema):
    assert schema.entity("shop_Tag").label == "shop.Tag"
    assert schema.entity("blog_Tag").label == "blog.Tag"
    assert schema.entity("Order").key == "Order"


def test_qualified_keys():
    schema = build_schema(select_models(["shop"]), qualified=True)
    assert all(e.key == "shop_" + e.model_name for e in schema.entities)


def test_dangling_fk_keeps_attribute(schema):
    a = attrs(schema, "Post")["author"]
    assert a.references == "auth.User"
    assert not any(r.label == "author" for r in schema.relations)


def test_unique_and_verbose_name(schema):
    customer = attrs(schema, "Customer")
    assert customer["email"].unique and not customer["id"].unique
    assert customer["name"].verbose_name == "名稱"
    assert customer["email"].verbose_name == ""


def test_choices(schema):
    assert attrs(schema, "Order")["status"].choices
    assert not attrs(schema, "Order")["total"].choices


def test_deterministic_regardless_of_input_order():
    models = select_models()
    assert build_schema(models) == build_schema(list(reversed(models)))


def test_composite_primary_key():
    from django.db import models
    from django.test.utils import isolate_apps

    if not hasattr(models, "CompositePrimaryKey"):
        pytest.skip("CompositePrimaryKey needs Django 5.2+")

    with isolate_apps("tests.apps.shop"):

        class Membership(models.Model):
            pk = models.CompositePrimaryKey("group", "member")
            group = models.IntegerField()
            member = models.IntegerField()
            role = models.CharField(max_length=10)

            class Meta:
                app_label = "shop"

        schema = build_schema([Membership])
    a = {x.name: x for x in schema.entities[0].attributes}
    assert set(a) == {"group", "member", "role"}
    assert a["group"].pk and a["member"].pk and not a["role"].pk


def test_unknown_field_type_falls_back_to_class_name():
    from django.db import models

    from django_mermaid_erd.naming import field_type

    class ArrayField(models.Field):
        pass

    class MoneyField(models.DecimalField):
        pass

    assert field_type(ArrayField()) == ("array", "")
    assert field_type(MoneyField(max_digits=8, decimal_places=2)) == ("decimal", "8,2")
    assert field_type(models.CharField()) == ("string", "")
