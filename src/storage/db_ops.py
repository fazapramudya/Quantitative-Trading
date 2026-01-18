from .supabase_client import supabase
import csv


def sb_fetch(table_name: str, select_columns: str = "*", filter_column: str = None, filter_value: str = None) -> dict:
    """
    Reads data from a specified Supabase table with optional filtering.

    Args:
        table_name (str): The name of the table to query (e.g., "planets").
        select_columns (str, optional): The columns to select (e.g., "name, mass"). Defaults to "*".
        filter_column (str, optional): The column to apply an equality filter on. Defaults to None.
        filter_value (str, optional): The value for the equality filter. Defaults to None.

    Returns:
        dict: The response object from the Supabase client, containing data and/or error.
    """
    try:
        query = supabase.table(table_name).select(select_columns)

        if filter_column and filter_value is not None:
            query = query.eq(filter_column, filter_value)

        response = query.execute()

        return response.model_dump()
    
    except Exception as e:
        print(f"An error occurred during Supabase READ query: {e}")
        return {"error": str(e), "data": None, "status_code": 500}


def sb_insert(table_name: str, data: dict, upsert: bool = False) -> dict:
    """
    Memasukkan data baru. Jika upsert=True, akan mengupdate jika data sudah ada.
    """
    try:
        # LOGIKA PERBAIKAN:
        # Jika upsert=True, langsung panggil fungsi .upsert()
        # Jika upsert=False, panggil fungsi .insert()
        if upsert:
            response = supabase.table(table_name).upsert(data).execute()
        else:
            response = supabase.table(table_name).insert(data).execute()

        return response.model_dump()
    
    except Exception as e:
        print(f"An error occurred during Supabase INSERT query: {e}")
        return {"error": str(e), "data": None, "status_code": 500}


def sb_update(table_name: str, data: dict, filter_column: str, filter_value) -> dict:
    """
    Updates rows in a specified Supabase table that match the filter condition.
    
    Args:
        table_name (str): The name of the table to update.
        data (dict): The column-value pairs to update.
        filter_column (str): The column used to find the rows to update (e.g., "id").
        filter_value: The value for the equality filter (e.g., 5).

    Returns:
        dict: The response object from the Supabase client.
    """
    if not filter_column or filter_value is None:
        return {"error": "Filter column and value are required for UPDATE operations.", "data": None, "status_code": 400}

    try:
        response = (
            supabase.table(table_name)
            .update(data)
            .eq(filter_column, filter_value)
            .execute()
        )
        return response.model_dump()

    except Exception as e:
        print(f"An error occurred during Supabase UPDATE query: {e}")
        return {"error": str(e), "data": None, "status_code": 500}


def sb_delete(table_name: str, filter_column: str, filter_value) -> dict:
    """
    Deletes rows in a specified Supabase table that match the filter condition.

    Args:
        table_name (str): The name of the table to delete from.
        filter_column (str): The column used to find the rows to delete (e.g., "id").
        filter_value: The value for the equality filter (e.g., 5).

    Returns:
        dict: The response object from the Supabase client.
    """
    if not filter_column or filter_value is None:
        return {"error": "Filter column and value are required for DELETE operations.", "data": None, "status_code": 400}
    
    try:
        response = (
            supabase.table(table_name)
            .delete()
            .eq(filter_column, filter_value)
            .execute()
        )
        return response.model_dump()

    except Exception as e:
        print(f"An error occurred during Supabase DELETE query: {e}")
        return {"error": str(e), "data": None, "status_code": 500}
    

def sb_bulk_upsert(
    table_name: str,
    data: list[dict],
    batch_size: int = 1000,
    on_conflict: str = None
) -> dict:
    """
    Upserts a list of dictionaries in batches (chunks) to avoid timeouts.

    Args:
        table_name (str): The table name.
        data (list[dict]): List of dictionaries to insert/update.
        batch_size (int): Number of rows to send per request. Defaults to 1000.
        on_conflict (str): Column to check for uniqueness (e.g., 'id', 'email').

    Returns:
        dict: Summary of operations (total_rows, success_count, error_log).
    """
    if not data:
        return {"error": "No data provided", "status": 400}

    total_count = len(data)
    errors = []
    success_count = 0

    for i in range(0, total_count, batch_size):
        batch = data[i : i + batch_size]
        current_batch_num = (i // batch_size) + 1

        try:
            query = supabase.table(table_name).upsert(batch)
            
            if on_conflict:
                query = supabase.table(table_name).upsert(batch, on_conflict=on_conflict)
            
            query.execute()
            
            success_count += len(batch)

        except Exception as e:
            error_msg = f"Batch {current_batch_num} failed: {str(e)}"
            errors.append(error_msg)

    return {
        "status": "completed" if not errors else "partial_success",
        "total_rows": total_count,
        "success_count": success_count,
        "errors": errors
    }

def sb_bulk_upsert_csv(
    table_name: str, 
    file_path: str, 
    batch_size: int = 1000, 
    on_conflict: str = None, 
    delimiter: str = ","
) -> dict:
    """
    Reads a CSV (or TSV/other) file and performs a bulk upsert.
    
    Args:
        table_name (str): The table name.
        file_path (str): Path to the file.
        batch_size (int): Chunk size.
        on_conflict (str): Unique column constraint.
        delimiter (str): The character separating fields (e.g., ',' or ';' or '\t').
    """
    data = []

    try:
        with open(file_path, mode='r', encoding='utf-8-sig') as f:
            
            reader = csv.DictReader(f, delimiter=delimiter)
            
            for row in reader:
                cleaned_row = {k: (v if v != "" else None) for k, v in row.items()}
                data.append(cleaned_row)

        return sb_bulk_upsert(table_name, data, batch_size, on_conflict)

    except FileNotFoundError:
        return {"error": f"File not found: {file_path}", "status": 404}
    except Exception as e:
        return {"error": f"Error reading file: {str(e)}", "status": 500}
