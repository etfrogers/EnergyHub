
import pytest

from ..octopus_api import OctopusClient


@pytest.mark.parametrize('bad_code', ['Q', 'sadasiu', 'South Eng'])
def test_bad_region_code(bad_code):
    with pytest.raises(ValueError):
        OctopusClient(region_code=bad_code)


@pytest.mark.parametrize('good_code', [('A', 'A'),
                                       ('B', 'B'), ('P', 'P'),
                                       ('Southern England', 'H'), ('Northern Scotland', 'P')])
def test_good_region_code(good_code):
    # test runs without error
    client = OctopusClient(region_code=good_code[0])
    assert client.region_code == good_code[1]
