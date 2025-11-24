import pytest
from unittest.mock import MagicMock, patch, mock_open

from storage.db_ops import (
    sb_fetch, 
    sb_insert, 
    sb_update, 
    sb_delete, 
    sb_bulk_upsert, 
    sb_bulk_upsert_csv
)

@pytest.fixture
def mock_supabase():
    """
    Patches the 'supabase' object imported in src/storage/db_ops.py
    """
    with patch("storage.db_ops.supabase") as mock:
        query_builder = MagicMock()
        
        mock.table.return_value = query_builder
        query_builder.select.return_value = query_builder
        query_builder.insert.return_value = query_builder
        query_builder.upsert.return_value = query_builder
        query_builder.update.return_value = query_builder
        query_builder.delete.return_value = query_builder
        query_builder.eq.return_value = query_builder
        
        mock_response = MagicMock()
        mock_response.model_dump.return_value = {"data": [], "error": None}
        query_builder.execute.return_value = mock_response
        
        yield mock

def test_sb_fetch_basic(mock_supabase):
    sb_fetch("planets")
    
    mock_supabase.table.assert_called_with("planets")
    mock_supabase.table().select.assert_called_with("*")

def test_sb_fetch_with_filter(mock_supabase):
    sb_fetch("planets", select_columns="name", filter_column="id", filter_value=5)
    
    mock_supabase.table().select.assert_called_with("name")
    mock_supabase.table().select().eq.assert_called_with("id", 5)

def test_sb_fetch_error_handling(mock_supabase):
    mock_supabase.table.side_effect = Exception("DB Connection Fail")
    
    result = sb_fetch("planets")
    
    assert result["status_code"] == 500
    assert "DB Connection Fail" in result["error"]

def test_sb_insert_basic(mock_supabase):
    data = {"name": "Earth"}
    sb_insert("planets", data)
    
    mock_supabase.table().insert.assert_called_with(data)

def test_sb_insert_upsert(mock_supabase):
    data = {"name": "Mars"}
    sb_insert("planets", data, upsert=True)
    
    mock_supabase.table().insert.assert_called_with(data)
    mock_supabase.table().insert().upsert.assert_called_with(data)

def test_sb_update_success(mock_supabase):
    data = {"name": "Mars Updated"}
    sb_update("planets", data, filter_column="id", filter_value=1)
    
    mock_supabase.table().update.assert_called_with(data)
    mock_supabase.table().update().eq.assert_called_with("id", 1)

def test_sb_update_missing_filter(mock_supabase):
    result = sb_update("planets", {"a": 1}, filter_column=None, filter_value=None)
    
    assert result["status_code"] == 400
    assert "required" in result["error"]
    mock_supabase.table.assert_not_called()

def test_sb_delete_success(mock_supabase):
    sb_delete("planets", filter_column="id", filter_value=99)
    
    mock_supabase.table().delete.assert_called()
    mock_supabase.table().delete().eq.assert_called_with("id", 99)

def test_sb_delete_missing_filter(mock_supabase):
    result = sb_delete("planets", filter_column="", filter_value=None)
    assert result["status_code"] == 400

def test_sb_bulk_upsert_chunking(mock_supabase):
    data = [{"id": i} for i in range(25)]
    
    result = sb_bulk_upsert("large_table", data, batch_size=10)
    
    assert result["status"] == "completed"
    assert result["total_rows"] == 25
    assert result["success_count"] == 25
    
    assert mock_supabase.table().upsert.call_count == 3
    
    args, _ = mock_supabase.table().upsert.call_args_list[0]
    assert len(args[0]) == 10

def test_sb_bulk_upsert_empty(mock_supabase):
    result = sb_bulk_upsert("test", [])
    assert result["status"] == 400

def test_sb_bulk_upsert_partial_failure(mock_supabase):
    data = [{"id": 1}, {"id": 2}]
    
    mock_supabase.table().upsert().execute.side_effect = Exception("Batch failed")
    
    result = sb_bulk_upsert("test", data, batch_size=2)
    
    assert result["status"] == "partial_success"
    assert len(result["errors"]) > 0

def test_sb_bulk_upsert_csv(mock_supabase):
    csv_content = "id,name,price\n1,Apple,10\n2,Banana,"
    
    with patch("builtins.open", mock_open(read_data=csv_content)):
        result = sb_bulk_upsert_csv("products", "dummy.csv")
        
        assert result["status"] == "completed"
        call_args = mock_supabase.table().upsert.call_args[0][0]
        
        assert call_args[0]['price'] == "10" 
        assert call_args[1]['price'] is None 

def test_sb_bulk_upsert_csv_not_found():
    with patch("builtins.open", side_effect=FileNotFoundError):
        result = sb_bulk_upsert_csv("products", "missing.csv")
        assert result["status"] == 404