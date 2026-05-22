import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# ==========================================
# KONFIGURASI HALAMAN & KAMUS BAHASA
# ==========================================
st.set_page_config(page_title="4G KPI Dashboard", layout="wide")

# Kamus terjemahan (English & Indonesia)
text = {
    "title": {"English": "📊 4G Network Performance Dashboard", "Indonesia": "📊 Dashboard Performa Jaringan 4G"},
    "upload": {"English": "Upload 4G CSV File", "Indonesia": "Upload File CSV 4G"},
    "loading": {"English": "Reading data and applying filters...", "Indonesia": "Membaca data dan menyusun filter..."},
    "err_time": {"English": "Column 'Time' not found in the CSV file.", "Indonesia": "Kolom 'Time' tidak ditemukan dalam file CSV."},
    "sb_title": {"English": "🎛️ Dashboard Filters", "Indonesia": "🎛️ Filter Dashboard"},
    "sb_caption": {"English": "💡 *Leave the box empty to show ALL data for that category.*", "Indonesia": "💡 *Kosongkan kotak pilihan jika ingin menampilkan SEMUA data pada kategori tersebut.*"},
    "f_date": {"English": "1. Select Date", "Indonesia": "1. Pilih Tanggal"},
    "f_tower": {"English": "2. Select Tower ID", "Indonesia": "2. Pilih Tower ID"},
    "f_band": {"English": "3. Select Band Frequency", "Indonesia": "3. Pilih Band Frequency"},
    "f_cell": {"English": "4. Select Cell Name (MOEntity)", "Indonesia": "4. Pilih Cell Name (MOEntity)"},
    "trend": {"English": "📈 Parameter Trend", "Indonesia": "📈 Trend Parameter"},
    "all": {"English": "All", "Indonesia": "Semua"},
    "selected": {"English": "Selected", "Indonesia": "Terpilih"},
    "active": {"English": "Active Data", "Indonesia": "Data Aktif"},
    "date": {"English": "Date", "Indonesia": "Tanggal"},
    "kpi_sel": {"English": "Select KPIs to display on the chart:", "Indonesia": "Pilih KPI yang ingin ditampilkan pada grafik:"},
    "no_data": {"English": "⚠️ No data matches your filter combination.", "Indonesia": "⚠️ Tidak ada data yang cocok dengan kombinasi filter yang Anda pilih."},
    "kpi_warn": {"English": "💡 Please select at least one parameter above to show the chart.", "Indonesia": "💡 Silakan pilih minimal satu parameter pada kotak di atas untuk memunculkan chart."},
    "start": {"English": "📂 Please upload a CSV file above to start.", "Indonesia": "📂 Silakan upload file CSV di atas untuk memulai."}
}

# Pilihan Bahasa di Sidebar (Default: English)
lang = st.sidebar.selectbox("🌐 Language / Bahasa", ["English", "Indonesia"], index=0)
st.sidebar.markdown("---")

st.title(text["title"][lang])

# Memisahkan fungsi load data dan menambahkan cache agar filter lebih cepat
@st.cache_data
def load_and_preprocess_data(file):
    df = pd.read_csv(file)
    
    # Memastikan format waktu benar
    if 'Time' in df.columns:
        df['Time'] = pd.to_datetime(df['Time'])
        # Membuat kolom bantuan khusus Tanggal saja (tanpa Jam)
        df['Tanggal_Filter'] = df['Time'].dt.date
    else:
        return None
        
    # Memastikan data MOEntity bersih dari nilai kosong
    if 'MOEntity' in df.columns:
        df['MOEntity'] = df['MOEntity'].fillna('Unknown Cell')
        
    return df

# 1. Widget Upload File
uploaded_file = st.file_uploader(text["upload"][lang], type=["csv"])

if uploaded_file is not None:
    with st.spinner(text["loading"][lang]):
        df = load_and_preprocess_data(uploaded_file)
        
        if df is None:
            st.error(text["err_time"][lang])
            st.stop()
            
        # ==========================================
        # 2. SIDEBAR FILTERS (Multi-Select & Cascading)
        # ==========================================
        st.sidebar.header(text["sb_title"][lang])
        st.sidebar.caption(text["sb_caption"][lang])
        
        # --- Filter 1: Tanggal ---
        date_options = sorted(list(df['Tanggal_Filter'].unique()))
        selected_date = st.sidebar.multiselect(text["f_date"][lang], date_options, default=date_options)
        if selected_date:
            df = df[df['Tanggal_Filter'].isin(selected_date)]
            
        # --- Filter 2: Tower ID ---
        if 'TowerID' in df.columns:
            tower_options = sorted(list(df['TowerID'].dropna().unique()))
            selected_tower = st.sidebar.multiselect(text["f_tower"][lang], tower_options)
            if selected_tower:
                df = df[df['TowerID'].isin(selected_tower)]
            
        # --- Filter 3: Band Frequency ---
        if '(4G Cell FDD)BAND' in df.columns:
            band_options = sorted(list(df['(4G Cell FDD)BAND'].dropna().unique()))
            selected_band = st.sidebar.multiselect(text["f_band"][lang], band_options)
            if selected_band:
                df = df[df['(4G Cell FDD)BAND'].isin(selected_band)]
            
        # --- Filter 4: Cell Name (MOEntity) ---
        cell_options = sorted(list(df['MOEntity'].dropna().unique()))
        selected_cell = st.sidebar.multiselect(text["f_cell"][lang], cell_options)
        if selected_cell:
            df = df[df['MOEntity'].isin(selected_cell)]

        # ==========================================
        # 3. MESIN PENGHITUNG CERDAS KPI
        # ==========================================
        calculated_kpis = []
        num_cols = [col for col in df.columns if '_Num' in col]
        
        for num_col in num_cols:
            parts = num_col.split('_Num')
            prefix = parts[0]
            suffix = parts[1] if len(parts) > 1 else ""
            
            den_col = None
            for c in df.columns:
                if c.startswith(prefix) and ('_Den' in c or '_DeNum' in c) and c.endswith(suffix):
                    den_col = c
                    break
            
            if den_col:
                base_name = f"{prefix}{suffix}"
                keywords = ['RATE', 'RATIO', 'CSSR', 'LOSS']
                is_percent = any(kw in base_name.upper() for kw in keywords)
                
                if is_percent:
                    new_kpi_name = f"✅ {base_name} (%)"
                    df[new_kpi_name] = np.where(df[den_col] == 0, 0, (df[num_col] / df[den_col]) * 100)
                else:
                    new_kpi_name = f"✅ {base_name}"
                    df[new_kpi_name] = np.where(df[den_col] == 0, 0, (df[num_col] / df[den_col]))
                
                if new_kpi_name not in calculated_kpis:
                    calculated_kpis.append(new_kpi_name)

        ready_kpis = [col for col in df.columns if '_KPI' in col]
        for col in ready_kpis:
            new_col_name = f"📊 {col}"
            df.rename(columns={col: new_col_name}, inplace=True)
            
        ready_kpis = [f"📊 {col}" for col in ready_kpis]
        all_final_kpis = ready_kpis + calculated_kpis

        # ==========================================
        # 4. RENDER DASHBOARD & CHART
        # ==========================================
        st.subheader(text["trend"][lang])
        
        def format_filter_text(selection):
            if not selection: return text["all"][lang]
            if len(selection) <= 3: return ", ".join(map(str, selection))
            return f"{len(selection)} {text['selected'][lang]}"

        st.caption(f"**{text['active'][lang]}:** {text['date'][lang]}: `{format_filter_text(selected_date)}` | Tower: `{format_filter_text(selected_tower if 'TowerID' in df.columns else [])}` | Band: `{format_filter_text(selected_band if '(4G Cell FDD)BAND' in df.columns else [])}` | Cell: `{format_filter_text(selected_cell)}`")

        selected_kpis = st.multiselect(
            text["kpi_sel"][lang], 
            options=all_final_kpis, 
            default=all_final_kpis[:4] if len(all_final_kpis) >= 4 else all_final_kpis
        )
        
        if selected_kpis:
            df_grouped = df.groupby(['Time', 'MOEntity'])[selected_kpis].mean().reset_index()
            
            if df_grouped.empty:
                st.warning(text["no_data"][lang])
            else:
                # Urutkan data berdasarkan MOEntity secara alfabetis (A-Z) untuk Legenda
                df_grouped = df_grouped.sort_values(by=['MOEntity', 'Time'])
                
                cols = st.columns(2)
                for i, kpi in enumerate(selected_kpis):
                    fig = px.line(
                        df_grouped, 
                        x='Time', 
                        y=kpi, 
                        color='MOEntity', 
                        title=kpi, 
                        markers=True
                    )
                    
                    if '(%)' in kpi:
                        fig.update_layout(yaxis=dict(range=[0, 105]))
                        
                    # Legenda orientasi vertikal (atas-bawah) di sebelah kanan luar chart
                    fig.update_layout(
                        height=400, 
                        margin=dict(l=20, r=20, t=40, b=20),
                        legend=dict(
                            orientation="v",        
                            font=dict(size=10),     
                            yanchor="top",
                            y=1,
                            xanchor="left",
                            x=1.02                  
                        )
                    )
                    cols[i % 2].plotly_chart(fig, use_container_width=True)
        else:
            st.info(text["kpi_warn"][lang])
            
else:
    st.info(text["start"][lang])