import pytest

from app.patterns.builder import MAX_PAGE_SIZE, MediaQuery, MediaQueryBuilder


def test_empty_builder_produces_default_query():
    assert MediaQueryBuilder().build() == MediaQuery()


def test_builder_chains_steps_and_ignores_empty_values():
    query = (
        MediaQueryBuilder()
        .title("  last minute goal  ")
        .genre(7)
        .year(None)       # skipped
        .country(None)    # skipped
        .media_type("movie")
        .build()
    )

    assert query.title == "last minute goal"
    assert query.genre_id == 7
    assert query.year is None
    assert query.country_id is None
    assert query.media_type == "movie"


def test_blank_title_is_ignored():
    assert MediaQueryBuilder().title("   ").build().title is None


def test_paginate_clamps_values_and_computes_offset():
    query = MediaQueryBuilder().paginate(page=3, page_size=1000).build()

    assert query.page_size == MAX_PAGE_SIZE
    assert query.offset == 2 * MAX_PAGE_SIZE


def test_unknown_media_type_is_rejected():
    with pytest.raises(ValueError):
        MediaQueryBuilder().media_type("cartoon")