import os

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
import seaborn as sns
import streamlit as st

sns.set_theme(style="whitegrid")
st.set_page_config(page_title="Olist E-Commerce Dashboard", page_icon="🛒", layout="wide")

BUCKET_ORDER = ["Tepat waktu / lebih cepat", "Telat 1-3 hari", "Telat 4-7 hari", "Telat > 7 hari"]
BUCKET_COLORS = ["#55A868", "#DD8452", "#C44E52", "#8B1E2D"]


@st.cache_data
def load_data():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main_data.csv")
    df = pd.read_csv(path, parse_dates=["order_purchase_timestamp", "order_delivered_customer_date",
                                        "order_estimated_delivery_date"])
    df["is_late"] = df["is_late"].astype(bool)
    return df


def build_rfm(df):
    snapshot = df["order_purchase_timestamp"].max().normalize() + pd.Timedelta(days=1)
    rfm = (df.groupby("customer_unique_id")
           .agg(last_purchase=("order_purchase_timestamp", "max"), frequency=("order_id", "nunique"),
                price=("price", "sum"), freight=("freight_value", "sum")))
    rfm["monetary"] = rfm["price"] + rfm["freight"]
    rfm["recency"] = (snapshot - rfm["last_purchase"]).dt.days
    rfm["R_score"] = pd.qcut(rfm["recency"].rank(method="first"), 4, labels=[4, 3, 2, 1]).astype(int)
    rfm["F_score"] = pd.cut(rfm["frequency"], bins=[0, 1, 2, np.inf], labels=[1, 2, 3]).astype(int)
    rfm["M_score"] = pd.qcut(rfm["monetary"].rank(method="first"), 4, labels=[1, 2, 3, 4]).astype(int)

    def segment(r):
        if r["F_score"] >= 2:
            return "Repeat Customer"
        if r["R_score"] >= 3:
            return "Baru - Belanja Besar" if r["M_score"] >= 3 else "Baru - Belanja Kecil"
        return "Berisiko Hilang - Belanja Besar" if r["M_score"] >= 3 else "Tidak Aktif - Belanja Kecil"

    rfm["segment"] = rfm.apply(segment, axis=1)
    return rfm


df = load_data()

# ---------------- Sidebar ----------------
st.sidebar.title("Filter")
min_d, max_d = df["order_purchase_timestamp"].min().date(), df["order_purchase_timestamp"].max().date()
date_range = st.sidebar.date_input("Periode pembelian", value=(min_d, max_d), min_value=min_d, max_value=max_d)
states = sorted(df["customer_state"].dropna().unique())
sel_states = st.sidebar.multiselect("State pelanggan", states, default=[], placeholder="Semua state")

if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    start, end = date_range
else:
    start, end = min_d, max_d

mask = (df["order_purchase_timestamp"].dt.date >= start) & (df["order_purchase_timestamp"].dt.date <= end)
if sel_states:
    mask &= df["customer_state"].isin(sel_states)
fdf = df[mask]

if fdf.empty:
    st.warning("Tidak ada data pada filter yang dipilih.")
    st.stop()

orders = fdf.drop_duplicates("order_id")

# ---------------- Header & KPI ----------------
st.title("🛒 Dashboard Analisis Olist E-Commerce")
st.caption("Pesanan berstatus delivered, Jan 2017 - Agu 2018 | Sumber: Brazilian E-Commerce Public Dataset by Olist")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Revenue", f"R$ {fdf['price'].sum():,.0f}")
k2.metric("Jumlah Pesanan", f"{orders['order_id'].nunique():,}")
k3.metric("Rata-rata Review", f"{orders['review_score'].mean():.2f} / 5")
k4.metric("Pesanan Terlambat", f"{orders['is_late'].mean():.1%}")

tab1, tab2, tab3 = st.tabs(["📦 Kategori Produk", "🚚 Pengiriman & Review", "👥 RFM Pelanggan"])

# ---------------- Tab 1: Pertanyaan 1 ----------------
with tab1:
    st.subheader("10 kategori dengan revenue terbesar & pertumbuhannya")
    cat = fdf.groupby("product_category_english")["price"].sum().sort_values(ascending=False)
    top10 = cat.head(10)
    st.write(f"10 kategori teratas menyumbang **{top10.sum() / cat.sum():.1%}** dari revenue pada filter yang dipilih.")

    # pertumbuhan: Jan-Agu 2018 vs Jan-Agu 2017 (tidak mengikuti filter tanggal, mengikuti filter state)
    base = df[df["customer_state"].isin(sel_states)] if sel_states else df
    ja = base[base["order_purchase_timestamp"].dt.month <= 8]
    rev_year = ja.pivot_table(index="product_category_english", columns=ja["order_purchase_timestamp"].dt.year,
                              values="price", aggfunc="sum")
    growth = ((rev_year[2018] / rev_year[2017] - 1) * 100).reindex(top10.index)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5), gridspec_kw={"width_ratios": [1.2, 1]})
    d = top10.iloc[::-1]
    labels = d.index.str.replace("_", " ").str.title()
    bars = axes[0].barh(labels, d / 1e6, color="#4C72B0")
    bars[-1].set_color("#1F3F77")
    for b, v in zip(bars, d / 1e6):
        axes[0].text(v + d.max() / 1e6 * 0.01, b.get_y() + b.get_height() / 2, f"{v:.2f}", va="center", fontsize=9)
    axes[0].set_title("Total revenue (juta R$)", loc="left", fontweight="bold")
    axes[0].set_xlim(0, d.max() / 1e6 * 1.15)

    g = growth.iloc[::-1]
    axes[1].barh(labels, g.fillna(0), color=["#C44E52" if (x < 0) else "#55A868" for x in g.fillna(0)])
    for i, v in enumerate(g):
        if pd.notna(v):
            axes[1].text(v + (3 if v >= 0 else -3), i, f"{v:+.0f}%", va="center", ha="left" if v >= 0 else "right", fontsize=9)
    axes[1].axvline(0, color="black", linewidth=0.8)
    axes[1].set_yticklabels([])
    axes[1].set_title("Pertumbuhan Jan-Agu 2018 vs Jan-Agu 2017", loc="left", fontweight="bold")
    axes[1].xaxis.set_major_formatter(mtick.PercentFormatter())
    gmin, gmax = np.nanmin(g.values), np.nanmax(g.values)
    axes[1].set_xlim(min(gmin, 0) - 30, max(gmax, 0) + 40)
    for ax in axes:
        ax.grid(axis="y", visible=False)
    plt.tight_layout()
    st.pyplot(fig)
    st.caption("Pertumbuhan dihitung pada periode yang sama (Jan-Agu) dan tidak terpengaruh filter tanggal; hanya mengikuti filter state.")

# ---------------- Tab 2: Pertanyaan 2 ----------------
with tab2:
    st.subheader("Dampak keterlambatan terhadap review & wilayah dengan keterlambatan tertinggi")
    ov = orders.dropna(subset=["review_score"])
    rv = (ov.groupby("delay_bucket").agg(orders=("order_id", "count"), avg_review=("review_score", "mean"))
          .reindex(BUCKET_ORDER).dropna().reset_index())

    c1, c2 = st.columns(2)
    with c1:
        fig, ax = plt.subplots(figsize=(7, 5))
        cols = [BUCKET_COLORS[BUCKET_ORDER.index(b)] for b in rv["delay_bucket"]]
        bars = ax.bar(rv["delay_bucket"], rv["avg_review"], color=cols)
        for b, (_, r) in zip(bars, rv.iterrows()):
            ax.text(b.get_x() + b.get_width() / 2, r["avg_review"] + 0.05, f"{r['avg_review']:.2f}\n(n={int(r['orders']):,})",
                    ha="center", fontsize=9)
        ax.set_ylim(0, 5.3)
        ax.set_ylabel("Rata-rata review score")
        ax.set_title("Rata-rata review per kelompok keterlambatan", loc="left", fontweight="bold")
        ax.tick_params(axis="x", labelrotation=15)
        ax.grid(axis="x", visible=False)
        plt.tight_layout()
        st.pyplot(fig)
    with c2:
        min_orders = st.slider("Minimal jumlah pesanan per state", 50, 1000, 300, step=50)
        stt = (orders.groupby("customer_state")
               .agg(orders=("order_id", "count"), late_pct=("is_late", lambda s: s.mean() * 100))
               .query("orders >= @min_orders").sort_values("late_pct", ascending=False))
        if stt.empty:
            st.info("Tidak ada state yang memenuhi batas minimal pesanan.")
        else:
            top = stt.head(10).sort_values("late_pct")
            nat = orders["is_late"].mean() * 100
            fig, ax = plt.subplots(figsize=(7, 5))
            highlight = set(stt.head(5).index)
            ax.barh(top.index, top["late_pct"], color=["#C44E52" if s in highlight else "#B0B7C3" for s in top.index])
            for i, v in enumerate(top["late_pct"]):
                ax.text(v + 0.2, i, f"{v:.1f}%", va="center", fontsize=9)
            ax.axvline(nat, color="black", linestyle="--", linewidth=1)
            ax.text(nat + 0.2, -0.75, f"rata-rata {nat:.1f}%", fontsize=9)
            ax.set_title("State dengan % pesanan terlambat tertinggi", loc="left", fontweight="bold")
            ax.xaxis.set_major_formatter(mtick.PercentFormatter())
            ax.grid(axis="y", visible=False)
            plt.tight_layout()
            st.pyplot(fig)

# ---------------- Tab 3: RFM ----------------
with tab3:
    st.subheader("Segmentasi pelanggan dengan RFM (binning manual)")
    st.write("Recency = hari sejak pembelian terakhir, Frequency = jumlah pesanan, Monetary = total harga + ongkir. "
             "Skor R & M memakai kuartil, skor F memakai batas manual (1, 2, 3+ pesanan).")
    rfm = build_rfm(fdf)
    order = ["Repeat Customer", "Baru - Belanja Besar", "Baru - Belanja Kecil",
             "Berisiko Hilang - Belanja Besar", "Tidak Aktif - Belanja Kecil"]
    seg = (rfm.groupby("segment").agg(customers=("recency", "count"), avg_recency=("recency", "mean"),
                                      avg_monetary=("monetary", "mean"), total=("monetary", "sum"))
           .reindex(order).dropna(how="all"))
    seg["customers_%"] = seg["customers"] / seg["customers"].sum() * 100
    seg["revenue_%"] = seg["total"] / seg["total"].sum() * 100

    fig, axes = plt.subplots(1, 2, figsize=(14, 4.5), sharey=True)
    y = seg.index.str.replace(" - ", "\n").tolist()
    for ax, col, color, ttl in [(axes[0], "customers_%", "#4C72B0", "% jumlah pelanggan"),
                                (axes[1], "revenue_%", "#55A868", "% total belanja")]:
        ax.barh(y, seg[col], color=color)
        for i, v in enumerate(seg[col]):
            ax.text(v + 0.5, i, f"{v:.1f}%", va="center", fontsize=9)
        ax.set_title(ttl, loc="left", fontweight="bold")
        ax.xaxis.set_major_formatter(mtick.PercentFormatter())
        ax.set_xlim(0, seg[col].max() * 1.2)
        ax.grid(axis="y", visible=False)
    axes[0].invert_yaxis()
    plt.tight_layout()
    st.pyplot(fig)
    st.dataframe(seg[["customers", "avg_recency", "avg_monetary", "customers_%", "revenue_%"]].round(1))

st.caption("© Septyan Yaumul Fatkhan | alfseptyan")
