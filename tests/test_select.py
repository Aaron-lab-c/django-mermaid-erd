import pytest

from django_mermaid_erd import build_schema
from django_mermaid_erd.exceptions import MermaidErdError
from django_mermaid_erd.select import entity_key_for, find_model, focus_schema, select_models


def labels(models):
    return {"%s.%s" % (m._meta.app_label, m._meta.object_name) for m in models}


def test_default_excludes_builtin():
    assert {label.split(".")[0] for label in labels(select_models())} == {"shop", "blog", "inventory"}


def test_include_builtin():
    got = labels(select_models(include_builtin=True))
    assert {"auth.User", "contenttypes.ContentType"} <= got


def test_explicit_builtin_app_is_included():
    assert labels(select_models(["auth"])) == {"auth.User", "auth.Group", "auth.Permission"}


def test_targets_app_and_model():
    got = labels(select_models(["blog", "shop.Order", "shop.order"]))
    assert "shop.Order" in got and "shop.Customer" not in got and "blog.Post" in got


def test_exclude_globs():
    got = labels(select_models(exclude=["inventory", "shop.*Tag", "BLOG.post"]))
    assert not any(label.startswith("inventory.") for label in got)
    assert "shop.ProductTag" not in got and "shop.Tag" not in got
    assert "blog.Post" not in got and "blog.Tag" in got


def test_no_proxy():
    assert "blog.PublishedPost" not in labels(select_models(include_proxy=False))


@pytest.mark.parametrize(
    "target, message",
    [
        ("nope", "Unknown app label 'nope'"),
        ("shop.Nope", "App 'shop' has no model named 'Nope'"),
    ],
)
def test_unknown_targets(target, message):
    with pytest.raises(MermaidErdError, match=message):
        select_models([target])


def test_find_model():
    assert find_model("order")._meta.object_name == "Order"
    with pytest.raises(MermaidErdError, match="ambiguous"):
        find_model("Tag")
    with pytest.raises(MermaidErdError, match="No model named"):
        find_model("Nope")


def test_focus_depth():
    schema = build_schema(select_models())
    key = entity_key_for(schema, "shop.Order")
    zero = focus_schema(schema, key, 0)
    assert [e.key for e in zero.entities] == ["Order"] and zero.relations == []
    one = {e.key for e in focus_schema(schema, key, 1).entities}
    assert one == {"Order", "Customer", "Coupon", "OrderItem"}
    two = {e.key for e in focus_schema(schema, key, 2).entities}
    assert two == one | {"Product"}
    assert focus_schema(schema, key, 1).apps == ["shop"]
