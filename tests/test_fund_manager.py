from invest.data.providers.eastmoney_fund import (
    _manager_detail_usable,
    _parse_manager_detail,
    _parse_manager_list_rows,
    _split_csv_field,
)


def test_split_csv_field():
    assert _split_csv_field("a,b, c") == ["a", "b", "c"]
    assert _split_csv_field("") == []
    assert _split_csv_field(None) == []


def test_parse_manager_list_current_only():
    rows = [
        {
            "MGRID": "111,222",
            "MGRNAME": "张三,李四",
            "FCODE": "110011",
            "FEMPDATE": "2020-01-01,2021-06-01",
            "LEMPDATE": "--,--",
            "DAYS": "100,50",
            "PENAVGROWTH": "10.5,20",
            "ISINOFFICE": "1,1",
        }
    ]
    current = _parse_manager_list_rows("110011", rows, current_only=True)
    assert len(current) == 2
    assert current[0].mgr_id == "111"
    assert current[0].name == "张三"
    assert current[0].tenure_return_pct == 10.5
    assert current[1].mgr_id == "222"


def test_parse_manager_list_skips_former():
    rows = [
        {
            "MGRID": "999",
            "MGRNAME": "王五",
            "LEMPDATE": "2023-12-31",
            "ISINOFFICE": "0",
        }
    ]
    current = _parse_manager_list_rows("110011", rows, current_only=True)
    assert current == []


def test_manager_detail_usable():
    assert _manager_detail_usable({"MGRNAME": "张三"})
    assert not _manager_detail_usable({})


def test_parse_manager_detail():
    info = {
        "MGRNAME": "测试经理",
        "COMPNAME": "测试公司",
        "RESUME": "简介文字",
        "FCODES": "110011,110022",
        "SHORTNAME": "基金A,基金B",
    }
    p = _parse_manager_detail("12345", info)
    assert p.mgr_id == "12345"
    assert p.name == "测试经理"
    assert p.managed_fund_codes == ["110011", "110022"]
    assert p.managed_fund_names == ["基金A", "基金B"]
