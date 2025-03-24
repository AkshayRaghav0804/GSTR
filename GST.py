import streamlit as st
import fitz  # PyMuPDF
import pdfplumber
import re
import pandas as pd
from pathlib import Path
 
# Set Streamlit page layout
st.set_page_config(layout="wide")
 
# Define the path to assets directory
ASSETS_DIR = Path("assets")
 
# Create assets directory if it doesn't exist
ASSETS_DIR.mkdir(exist_ok=True)
 
# Add logo to the sidebar
logo_path = ASSETS_DIR / "kkc logo.png"
if logo_path.exists():
    st.sidebar.image(str(logo_path), width=275)
else:
    st.sidebar.warning("Logo file not found. Please place 'kkc logo.png' in the assets directory.")
# After the logo display code in the sidebar section

# Add User Manual download button below the logo
manual_path = ASSETS_DIR / "User Manual.pdf"
if manual_path.exists():
    with open(manual_path, "rb") as manual_file:
        st.sidebar.download_button(
            label="📄 Download User Manual",
            data=manual_file,
            file_name="GST_Extractor_User_Manual.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
else:
    st.sidebar.warning("User manual not found. Please place 'user_manual.pdf' in the assets directory.")
 
# Add sidebar for GST type selection
st.sidebar.title("GST Return Type")
gst_type = st.sidebar.radio("Select GST Return Type", ["GSTR-1", "GSTR-3B"])

# Add refresh note
st.sidebar.info("🔄 Kindly refresh the page to upload new files or start again.")
 
# GST State Code Mapping
GST_STATE_CODES = {
    "01": "Jammu and Kashmir", "02": "Himachal Pradesh", "03": "Punjab", "04": "Chandigarh",
    "05": "Uttarakhand", "06": "Haryana", "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh",
    "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh", "13": "Nagaland", "14": "Manipur",
    "15": "Mizoram", "16": "Tripura", "17": "Meghalaya", "18": "Assam", "19": "West Bengal",
    "20": "Jharkhand", "21": "Odisha", "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
    "26": "Dadra and Nagar Haveli and Daman and Diu", "27": "Maharashtra", "29": "Karnataka",
    "30": "Goa", "31": "Lakshadweep", "32": "Kerala", "33": "Tamil Nadu", "34": "Puducherry",
    "35": "Andaman and Nicobar Islands", "36": "Telangana", "37": "Andhra Pradesh", "38": "Ladakh",
    "97": "Other Territory", "99": "Centre Jurisdiction",
}

# Helper function to get state from GSTIN
def get_state_from_gstin(gstin):
    if not gstin or len(gstin) < 2:
        return "Unknown"
    state_code = gstin[:2]
    return GST_STATE_CODES.get(state_code, "Unknown")
 
# GSTR-1 Functions
def extract_details(pdf_path):
    details = {"GSTIN": "", "State": "", "Legal Name": "", "Month": "", "Financial Year": ""}
   
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                gstin_match = re.search(r'GSTIN\s*[:\-]?\s*(\d{2}[A-Z0-9]{13})', text)
                if gstin_match:
                    details["GSTIN"] = gstin_match.group(1)
                    details["State"] = GST_STATE_CODES.get(details["GSTIN"][:2], "Unknown")
               
                legal_name_match = re.search(r'Legal name of the registered person\s*[:\-]?\s*(.*)', text)
                if legal_name_match:
                    details["Legal Name"] = legal_name_match.group(1).strip()
               
                month_match = re.search(r'Tax period\s*[:\-]?\s*(\w+)', text)
                if month_match:
                    details["Month"] = month_match.group(1).strip()
               
                fy_match = re.search(r'Financial year\s*[:\-]?\s*(\d{4}-\d{2})', text)
                if fy_match:
                    details["Financial Year"] = fy_match.group(1).strip()
               
                break
    return details
 
def extract_total_liability(pdf_bytes):
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        text = "\n".join([page.get_text("text") for page in doc])
   
    pattern = r"Total Liability \(Outward supplies other than Reverse charge\)\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)"
    match = re.search(pattern, text)
   
    if match:
        return [match.group(1), match.group(2), match.group(3), match.group(4), match.group(5)]
    return ["Not Found", "", "", "", ""]

# New function to extract Tables 4A and 4B
def extract_tables_4A_4B(pdf_bytes):
    tables = {
        "4A": {
            "description": "Taxable outward supplies made to registered persons (other than reverse charge supplies)",
            "title": "B2B Regular",
            "data": None
        },
        "4B": {
            "description": "Taxable outward supplies made to registered persons attracting tax on reverse charge",
            "title": "B2B Reverse charge",
            "data": None
        }
    }
    
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        text = "\n".join([page.get_text("text") for page in doc])
        
        # Extract Table 4A
        pattern_4A = r"4A - Taxable outward supplies made to registered persons.*?Total\s+(\d+)\s+Invoice\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)"
        match_4A = re.search(pattern_4A, text, re.DOTALL)
        
        if match_4A:
            tables["4A"]["data"] = {
                "No. of records": match_4A.group(1),
                "Value": match_4A.group(2),
                "Integrated Tax": match_4A.group(3),
                "Central Tax": match_4A.group(4),
                "State/UT Tax": match_4A.group(5),
                "Cess": match_4A.group(6)
            }
        
        # Extract Table 4B
        pattern_4B = r"4B - Taxable outward supplies made to registered persons attracting tax on reverse charge.*?Total\s+(\d+)\s+Invoice\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)\s+([\d,]+\.\d+)"
        match_4B = re.search(pattern_4B, text, re.DOTALL)
        
        if match_4B:
            tables["4B"]["data"] = {
                "No. of records": match_4B.group(1),
                "Value": match_4B.group(2),
                "Integrated Tax": match_4B.group(3),
                "Central Tax": match_4B.group(4),
                "State/UT Tax": match_4B.group(5),
                "Cess": match_4B.group(6)
            }
    
    return tables
 
# GSTR-3B Functions
def clean_numeric_value(value):
    if value is None:
        return 0.0
   
    if isinstance(value, str):
        value = value.replace("E", "").replace("F", "").strip()
   
    try:
        return float(value.replace(",", ""))
    except ValueError:
        return 0.0
 
def extract_general_details(text):
    def safe_extract(pattern, text):
        match = re.search(pattern, text)
        return match.group(1).strip() if match else None
   
    gstin = safe_extract(r"GSTIN\s+([A-Z0-9]+)", text)
    state = get_state_from_gstin(gstin)
    
    return {
        "GSTIN": gstin,
        "State": state,
        "Legal Name": safe_extract(r"Legal name of the registered person\s+(.+)", text),
        "Date": safe_extract(r"Date of ARN\s+([\d/]+)", text),
        "Financial Year": safe_extract(r"Year\s+(\d{4}-\d{2})", text),
        "Period": safe_extract(r"Period\s+([A-Za-z]+)", text),
    }
 
def extract_table_4(pdf):
    expected_rows = [
        "A. ITC Available (whether in full or part)",
        "(1) Import of goods",
        "(2) Import of services",
        "(3) Inward supplies liable to reverse charge",
        "(4) Inward supplies from ISD",
        "(5) All other ITC",
        "B. ITC Reversed",
        "(1) As per rules 38,42 & 43 of CGST Rules and section 17(5)",
        "(2) Others",
        "C. Net ITC available (A-B)",
        "D. Other Details",
        "(1) ITC reclaimed which was reversed under Table 4(B)(2) in earlier tax period",
        "(2) Ineligible ITC under section 16(4) & ITC restricted due to PoS rules"
    ]
   
    value_map = {}
    table_started = False
   
    for page in pdf.pages:
        text = page.extract_text()
        tables = page.extract_tables()
       
        if "4. Eligible ITC" in text or "Eligible ITC" in text:
            table_started = True
       
        if table_started:
            for table in tables:
                if not table:
                    continue
               
                for row in table:
                    if not row or len(row) < 4:
                        continue
                   
                    row = [str(cell).strip() if cell is not None else '' for cell in row]
                    row_text = row[0]
                   
                    if "Details" in row_text or "Integrated" in row_text:
                        continue
                   
                    values = []
                    for cell in row[1:5]:
                        try:
                            value = clean_numeric_value(cell)
                            values.append(value)
                        except:
                            values.append(0.0)
                   
                    while len(values) < 4:
                        values.append(0.0)
                   
                    for expected_row in expected_rows:
                        if expected_row.lower().replace(" ", "") in row_text.lower().replace(" ", ""):
                            value_map[expected_row] = values
                            break
           
            if "5." in text or "Details of amount paid" in text or "Payment of tax" in text:
                break
   
    data = []
    for row_header in expected_rows:
        if row_header in value_map:
            data.append([row_header] + value_map[row_header])
        else:
            data.append([row_header] + [0.0] * 4)
   
    df = pd.DataFrame(data, columns=["Details", "Integrated Tax", "Central Tax", "State/UT Tax", "Cess"])
    return df
 
def extract_table_3_1(pdf):
    expected_columns = ["Nature of Supplies", "Total Taxable Value", "Integrated Tax", "Central Tax", "State/UT Tax", "Cess"]
   
    for page in pdf.pages:
        text = page.extract_text()
        if "3.1" in text and "Nature of Supplies" in text:
            table = page.extract_table()
            if table:
                df = pd.DataFrame(table[1:], columns=table[0])
                df = df.iloc[:, :len(expected_columns)]
                df.columns = expected_columns
               
                for col in expected_columns[1:]:
                    df[col] = df[col].apply(clean_numeric_value)
                return df
   
    return pd.DataFrame(columns=expected_columns)
 
def extract_table_6_1(pdf):
    expected_columns = ["Description", "Total Tax Payable", "Tax Paid Through ITC",
                       "Tax Paid in Cash", "Interest Paid in Cash", "Late Fee Paid in Cash"]
   
    for page in pdf.pages:
        text = page.extract_text()
        if "Payment of tax" in text:
            table = page.extract_table()
            if table:
                df = pd.DataFrame(table[1:], columns=table[0])
                df = df.iloc[:, :len(expected_columns)]
                df.columns = expected_columns
               
                for col in expected_columns[1:]:
                    df[col] = df[col].apply(clean_numeric_value)
                return df
   
    return pd.DataFrame(columns=expected_columns)
 
def create_combined_gstr3b_sheet(general_df, table_3_1_df, table_4_df, table_6_1_df):
    """
    Create a single combined sheet with all GSTR-3B data organized systematically
    """
    # Initialize an empty DataFrame for the combined sheet
    combined_df = pd.DataFrame()
   
    # Process all files
    unique_files = set(table_3_1_df["File Name"].unique()) | set(table_4_df["File Name"].unique()) | set(table_6_1_df["File Name"].unique())
   
    rows = []
   
    for idx, file_name in enumerate(unique_files):
        # Get general details for this file
        file_general_details = general_df[general_df.index == idx].to_dict(orient='records')
        if file_general_details:
            general_info = file_general_details[0]
        else:
            general_info = {"GSTIN": "Unknown", "Legal Name": "Unknown", "Date": "Unknown",
                           "Financial Year": "Unknown", "Period": "Unknown", "State": "Unknown"}
       
        # Create a row with file and general information
        base_row = {
            "File Name": file_name,
            "GSTIN": general_info.get("GSTIN", "Unknown"),
            "State": general_info.get("State", "Unknown"),
            "Legal Name": general_info.get("Legal Name", "Unknown"),
            "Date": general_info.get("Date", "Unknown"),
            "Financial Year": general_info.get("Financial Year", "Unknown"),
            "Period": general_info.get("Period", "Unknown"),
            "Data Type": "",
            "Description": "",
            "Total Taxable Value": 0.0,
            "Integrated Tax": 0.0,
            "Central Tax": 0.0,
            "State/UT Tax": 0.0,
            "Cess": 0.0,
            "Total Tax Payable": 0.0,
            "Tax Paid Through ITC": 0.0,
            "Tax Paid in Cash": 0.0,
            "Interest Paid in Cash": 0.0,
            "Late Fee Paid in Cash": 0.0
        }
       
        # Add a header row for this file
        header_row = base_row.copy()
        header_row["Data Type"] = "FILE INFO"
        header_row["Description"] = "File Information"
        rows.append(header_row)
       
        # Add 3.1 data
        file_table_3_1 = table_3_1_df[table_3_1_df["File Name"] == file_name]
        if not file_table_3_1.empty:
            for _, row in file_table_3_1.iterrows():
                data_row = base_row.copy()
                data_row["Data Type"] = "Table 3.1"
                data_row["Description"] = row.get("Nature of Supplies", "")
                data_row["Total Taxable Value"] = row.get("Total Taxable Value", 0.0)
                data_row["Integrated Tax"] = row.get("Integrated Tax", 0.0)
                data_row["Central Tax"] = row.get("Central Tax", 0.0)
                data_row["State/UT Tax"] = row.get("State/UT Tax", 0.0)
                data_row["Cess"] = row.get("Cess", 0.0)
                rows.append(data_row)
       
        # Add Table 4 data
        file_table_4 = table_4_df[table_4_df["File Name"] == file_name]
        if not file_table_4.empty:
            for _, row in file_table_4.iterrows():
                data_row = base_row.copy()
                data_row["Data Type"] = "Table 4"
                data_row["Description"] = row.get("Details", "")
                data_row["Integrated Tax"] = row.get("Integrated Tax", 0.0)
                data_row["Central Tax"] = row.get("Central Tax", 0.0)
                data_row["State/UT Tax"] = row.get("State/UT Tax", 0.0)
                data_row["Cess"] = row.get("Cess", 0.0)
                rows.append(data_row)
       
        # Add Table 6.1 data
        file_table_6_1 = table_6_1_df[table_6_1_df["File Name"] == file_name]
        if not file_table_6_1.empty:
            for _, row in file_table_6_1.iterrows():
                data_row = base_row.copy()
                data_row["Data Type"] = "Table 6.1"
                data_row["Description"] = row.get("Description", "")
                data_row["Total Tax Payable"] = row.get("Total Tax Payable", 0.0)
                data_row["Tax Paid Through ITC"] = row.get("Tax Paid Through ITC", 0.0)
                data_row["Tax Paid in Cash"] = row.get("Tax Paid in Cash", 0.0)
                data_row["Interest Paid in Cash"] = row.get("Interest Paid in Cash", 0.0)
                data_row["Late Fee Paid in Cash"] = row.get("Late Fee Paid in Cash", 0.0)
                rows.append(data_row)
       
        # Add a separator row
        separator_row = {k: "" for k in base_row.keys()}
        separator_row["Description"] = "----------------------"
        rows.append(separator_row)
   
    # Create DataFrame from rows
    combined_df = pd.DataFrame(rows)
    return combined_df
 
# Main Application Logic
if gst_type == "GSTR-1":
    st.title("📄 GSTR-1 Data Extraction Tool")
    st.write("Drag and Drop or Upload GSTR-1 PDFs to extract details")
   
    uploaded_files = st.file_uploader("", type=["pdf"], accept_multiple_files=True)
   
    if uploaded_files:
        data = []
        table_4A_data = []
        table_4B_data = []
        
        for uploaded_file in uploaded_files:
            pdf_bytes = uploaded_file.read()
            details = extract_details(uploaded_file)
            total_liability = extract_total_liability(pdf_bytes)
            data.append([uploaded_file.name] + list(details.values()) + total_liability)
            
            # Extract Tables 4A and 4B
            tables_4A_4B = extract_tables_4A_4B(pdf_bytes)
            
            # Process Table 4A
            if tables_4A_4B["4A"]["data"]:
                table_4A_data.append([
                    uploaded_file.name,
                    details["GSTIN"],
                    details["State"],  # Added State column here
                    details["Legal Name"],
                    details["Month"],
                    details["Financial Year"],
                    tables_4A_4B["4A"]["data"]["No. of records"],
                    tables_4A_4B["4A"]["data"]["Value"],
                    tables_4A_4B["4A"]["data"]["Integrated Tax"],
                    tables_4A_4B["4A"]["data"]["Central Tax"],
                    tables_4A_4B["4A"]["data"]["State/UT Tax"],
                    tables_4A_4B["4A"]["data"]["Cess"]
                ])
            
            # Process Table 4B
            if tables_4A_4B["4B"]["data"]:
                table_4B_data.append([
                    uploaded_file.name,
                    details["GSTIN"],
                    details["State"],  # Added State column here
                    details["Legal Name"],
                    details["Month"],
                    details["Financial Year"],
                    tables_4A_4B["4B"]["data"]["No. of records"],
                    tables_4A_4B["4B"]["data"]["Value"],
                    tables_4A_4B["4B"]["data"]["Integrated Tax"],
                    tables_4A_4B["4B"]["data"]["Central Tax"],
                    tables_4A_4B["4B"]["data"]["State/UT Tax"],
                    tables_4A_4B["4B"]["data"]["Cess"]
                ])
       
        columns = ["File Name", "GSTIN", "State", "Legal Name", "Month", "Financial Year", "Taxable Value", "IGST", "CGST", "SGST", "Cess"]
        df = pd.DataFrame(data, columns=columns)
        
        # Create DataFrames for Tables 4A and 4B
        columns_4AB = ["File Name", "GSTIN", "State", "Legal Name", "Month", "Financial Year", "No. of records", "Value", "Integrated Tax", "Central Tax", "State/UT Tax", "Cess"]
        df_4A = pd.DataFrame(table_4A_data, columns=columns_4AB)
        df_4B = pd.DataFrame(table_4B_data, columns=columns_4AB)
       
        st.write("### Total Liability (Outward supplies other than Reverse charge) ")
        st.dataframe(df)

       
        def multiselect_with_select_all(label, options):
            selected = st.multiselect(label, ["Select All"] + options, default=["Select All"])
            return options if "Select All" in selected else selected
       
        selected_month = multiselect_with_select_all("Filter by Month", df["Month"].unique().tolist())
        selected_state = multiselect_with_select_all("Filter by State", df["State"].unique().tolist())
        selected_gstin = multiselect_with_select_all("Filter by GSTIN", df["GSTIN"].unique().tolist())
        selected_legal_name = multiselect_with_select_all("Filter by Legal Name", df["Legal Name"].unique().tolist())
        selected_year = multiselect_with_select_all("Filter by Financial Year", df["Financial Year"].unique().tolist())
       
        filtered_df = df
        filtered_df_4A = df_4A
        filtered_df_4B = df_4B
        
        if selected_month:
            filtered_df = filtered_df[filtered_df["Month"].isin(selected_month)]
            filtered_df_4A = filtered_df_4A[filtered_df_4A["Month"].isin(selected_month)]
            filtered_df_4B = filtered_df_4B[filtered_df_4B["Month"].isin(selected_month)]
            
        if selected_state:
            filtered_df = filtered_df[filtered_df["State"].isin(selected_state)]
            filtered_df_4A = filtered_df_4A[filtered_df_4A["State"].isin(selected_state)]
            filtered_df_4B = filtered_df_4B[filtered_df_4B["State"].isin(selected_state)]
            
        if selected_gstin:
            filtered_df = filtered_df[filtered_df["GSTIN"].isin(selected_gstin)]
            filtered_df_4A = filtered_df_4A[filtered_df_4A["GSTIN"].isin(selected_gstin)]
            filtered_df_4B = filtered_df_4B[filtered_df_4B["GSTIN"].isin(selected_gstin)]
            
        if selected_legal_name:
            filtered_df = filtered_df[filtered_df["Legal Name"].isin(selected_legal_name)]
            filtered_df_4A = filtered_df_4A[filtered_df_4A["Legal Name"].isin(selected_legal_name)]
            filtered_df_4B = filtered_df_4B[filtered_df_4B["Legal Name"].isin(selected_legal_name)]
            
        if selected_year:
            filtered_df = filtered_df[filtered_df["Financial Year"].isin(selected_year)]
            filtered_df_4A = filtered_df_4A[filtered_df_4A["Financial Year"].isin(selected_year)]
            filtered_df_4B = filtered_df_4B[filtered_df_4B["Financial Year"].isin(selected_year)]
       
        st.write("### Filtered Results - Total Liability")
        st.dataframe(filtered_df)
        
        st.write("### Filtered Results - Table 4A")
        st.dataframe(filtered_df_4A)
        
        st.write("### Filtered Results - Table 4B")
        st.dataframe(filtered_df_4B)
       
        # Add Excel download functionality for GSTR-1
        output_excel = "GSTR1_Filtered.xlsx"
        with pd.ExcelWriter(output_excel) as writer:
            # Only include filtered data in the Excel file
            filtered_df.to_excel(writer, sheet_name="Filtered Total Liability", index=False)
            filtered_df_4A.to_excel(writer, sheet_name="Filtered Table 4A", index=False)
            filtered_df_4B.to_excel(writer, sheet_name="Filtered Table 4B", index=False)
       
        with open(output_excel, "rb") as f:
            st.download_button("Download Filtered Data as Excel", f, file_name="GSTR1_Filtered.xlsx")
 
else:  # GSTR-3B
    st.title("📄 GSTR-3B Data Extraction Tool")
    st.write("Drag and Drop or Upload GSTR-3B PDFs to extract details")
   
    uploaded_files = st.file_uploader("", type="pdf", accept_multiple_files=True)
   
    if uploaded_files:
        all_general_details = []
        all_table_3_1 = []
        all_table_4 = []
        all_table_6_1 = []
       
        for pdf_file in uploaded_files:
            with pdfplumber.open(pdf_file) as pdf:
                full_text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
               
                general_details = extract_general_details(full_text)
                all_general_details.append(general_details)
               
                table_3_1 = extract_table_3_1(pdf)
                table_3_1["File Name"] = pdf_file.name
                all_table_3_1.append(table_3_1)
               
                table_4 = extract_table_4(pdf)
                table_4["File Name"] = pdf_file.name
                all_table_4.append(table_4)
               
                table_6_1 = extract_table_6_1(pdf)
                table_6_1["File Name"] = pdf_file.name
                all_table_6_1.append(table_6_1)
       
        # 1) General Details
        st.subheader("General Details")
        general_df = pd.DataFrame(all_general_details)
        st.dataframe(general_df)
       
        # Process but don't display these tables
        final_table_3_1 = pd.concat(all_table_3_1, ignore_index=True)
        final_table_4 = pd.concat(all_table_4, ignore_index=True)
        final_table_6_1 = pd.concat(all_table_6_1, ignore_index=True)
        
        # Create combined data sheet
        combined_df = create_combined_gstr3b_sheet(general_df, final_table_3_1, final_table_4, final_table_6_1)
        
        # 2) Filters
        st.write("### Filter Data")
        
        def multiselect_with_select_all(label, options):
            selected = st.multiselect(label, ["Select All"] + options, default=["Select All"])
            return options if "Select All" in selected else selected
        
        # Extract unique values for filters
        months = general_df["Period"].dropna().unique().tolist()
        states = [GST_STATE_CODES.get(gstin[:2], "Unknown") if gstin else "Unknown" 
                 for gstin in general_df["GSTIN"].dropna().unique()]
        gstins = general_df["GSTIN"].dropna().unique().tolist()
        legal_names = general_df["Legal Name"].dropna().unique().tolist()
        financial_years = general_df["Financial Year"].dropna().unique().tolist()
        
        # Create filters
        selected_month = multiselect_with_select_all("Filter by Month", months)
        selected_state = multiselect_with_select_all("Filter by State", states)
        selected_gstin = multiselect_with_select_all("Filter by GSTIN", gstins)
        selected_legal_name = multiselect_with_select_all("Filter by Legal Name", legal_names)
        selected_year = multiselect_with_select_all("Filter by Financial Year", financial_years)
        
        # Apply filters to dataframes
        filtered_general_df = general_df.copy()
        filtered_table_3_1 = final_table_3_1.copy()
        filtered_table_4 = final_table_4.copy()
        filtered_table_6_1 = final_table_6_1.copy()
        filtered_combined_df = combined_df.copy()
        
        # Filter by Month (Period)
        if selected_month:
            filtered_general_df = filtered_general_df[filtered_general_df["Period"].isin(selected_month)]
            file_names = filtered_general_df.index.tolist()
            
            filtered_table_3_1 = filtered_table_3_1[filtered_table_3_1["File Name"].isin(
                [uploaded_files[i].name for i in file_names if i < len(uploaded_files)])]
            filtered_table_4 = filtered_table_4[filtered_table_4["File Name"].isin(
                [uploaded_files[i].name for i in file_names if i < len(uploaded_files)])]
            filtered_table_6_1 = filtered_table_6_1[filtered_table_6_1["File Name"].isin(
                [uploaded_files[i].name for i in file_names if i < len(uploaded_files)])]
            filtered_combined_df = filtered_combined_df[filtered_combined_df["Period"].isin(selected_month)]
        
        # Filter by State (derived from GSTIN)
        if selected_state:
            state_gstins = []
            for gstin in gstins:
                if gstin and GST_STATE_CODES.get(gstin[:2], "Unknown") in selected_state:
                    state_gstins.append(gstin)
            
            filtered_general_df = filtered_general_df[filtered_general_df["GSTIN"].isin(state_gstins)]
            file_names = filtered_general_df.index.tolist()
            
            filtered_table_3_1 = filtered_table_3_1[filtered_table_3_1["File Name"].isin(
                [uploaded_files[i].name for i in file_names if i < len(uploaded_files)])]
            filtered_table_4 = filtered_table_4[filtered_table_4["File Name"].isin(
                [uploaded_files[i].name for i in file_names if i < len(uploaded_files)])]
            filtered_table_6_1 = filtered_table_6_1[filtered_table_6_1["File Name"].isin(
                [uploaded_files[i].name for i in file_names if i < len(uploaded_files)])]
            filtered_combined_df = filtered_combined_df[filtered_combined_df["GSTIN"].isin(state_gstins)]
        
        # Filter by GSTIN
        if selected_gstin:
            filtered_general_df = filtered_general_df[filtered_general_df["GSTIN"].isin(selected_gstin)]
            file_names = filtered_general_df.index.tolist()
            
            filtered_table_3_1 = filtered_table_3_1[filtered_table_3_1["File Name"].isin(
                [uploaded_files[i].name for i in file_names if i < len(uploaded_files)])]
            filtered_table_4 = filtered_table_4[filtered_table_4["File Name"].isin(
                [uploaded_files[i].name for i in file_names if i < len(uploaded_files)])]
            filtered_table_6_1 = filtered_table_6_1[filtered_table_6_1["File Name"].isin(
                [uploaded_files[i].name for i in file_names if i < len(uploaded_files)])]
            filtered_combined_df = filtered_combined_df[filtered_combined_df["GSTIN"].isin(selected_gstin)]
        
        # Filter by Legal Name
        if selected_legal_name:
            filtered_general_df = filtered_general_df[filtered_general_df["Legal Name"].isin(selected_legal_name)]
            file_names = filtered_general_df.index.tolist()
            
            filtered_table_3_1 = filtered_table_3_1[filtered_table_3_1["File Name"].isin(
                [uploaded_files[i].name for i in file_names if i < len(uploaded_files)])]
            filtered_table_4 = filtered_table_4[filtered_table_4["File Name"].isin(
                [uploaded_files[i].name for i in file_names if i < len(uploaded_files)])]
            filtered_table_6_1 = filtered_table_6_1[filtered_table_6_1["File Name"].isin(
                [uploaded_files[i].name for i in file_names if i < len(uploaded_files)])]
            filtered_combined_df = filtered_combined_df[filtered_combined_df["Legal Name"].isin(selected_legal_name)]
        
        # Filter by Financial Year
        if selected_year:
            filtered_general_df = filtered_general_df[filtered_general_df["Financial Year"].isin(selected_year)]
            file_names = filtered_general_df.index.tolist()
            
            filtered_table_3_1 = filtered_table_3_1[filtered_table_3_1["File Name"].isin(
                [uploaded_files[i].name for i in file_names if i < len(uploaded_files)])]
            filtered_table_4 = filtered_table_4[filtered_table_4["File Name"].isin(
                [uploaded_files[i].name for i in file_names if i < len(uploaded_files)])]
            filtered_table_6_1 = filtered_table_6_1[filtered_table_6_1["File Name"].isin(
                [uploaded_files[i].name for i in file_names if i < len(uploaded_files)])]
            filtered_combined_df = filtered_combined_df[filtered_combined_df["Financial Year"].isin(selected_year)]
        
        # Display filtered results in order specified
        # 3) Filtered General Details
        st.write("### Filtered General Details")
        st.dataframe(filtered_general_df)
        
        # 4) Filtered Table 3.1
        st.write("### Filtered Table 3.1 - Outward and Reverse Charge Supplies")
        st.dataframe(filtered_table_3_1)
        
        # 5) Filtered Table 4
        st.write("### Filtered Table 4 - Eligible ITC")
        st.dataframe(filtered_table_4)
        
        # 6) Filtered Table 6.1
        st.write("### Filtered Table 6.1 - Payment of Tax")
        st.dataframe(filtered_table_6_1)
        
        # 7) Filtered Combined GSTR-3B Data
        st.write("### Filtered Combined GSTR-3B Data")
        st.dataframe(filtered_combined_df)
       
        output_excel = "GSTR3B_Filtered.xlsx"
        with pd.ExcelWriter(output_excel) as writer:
            # Only write filtered data to the Excel file
            filtered_combined_df.to_excel(writer, sheet_name="Filtered Combined Data", index=False)
            filtered_general_df.to_excel(writer, sheet_name="Filtered General Details", index=False)
            filtered_table_3_1.to_excel(writer, sheet_name="Filtered Table 3.1", index=False)
            filtered_table_4.to_excel(writer, sheet_name="Filtered Table 4", index=False)
            filtered_table_6_1.to_excel(writer, sheet_name="Filtered Table 6.1", index=False)
       
        with open(output_excel, "rb") as f:
            st.download_button("Download Filtered Data", f, file_name="GSTR3B_Filtered.xlsx")
