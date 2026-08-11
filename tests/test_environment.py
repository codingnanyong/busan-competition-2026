import geopandas as gpd
import pandas as pd
import plotly.express as px
import sklearn
from shapely.geometry import Point


def test_analysis_stack_imports_and_runs() -> None:
    frame = pd.DataFrame({"district": ["A", "B"], "score": [1.0, 2.0]})
    spatial = gpd.GeoDataFrame(
        frame,
        geometry=[Point(129.0756, 35.1796), Point(129.0810, 35.1700)],
        crs="EPSG:4326",
    )
    figure = px.bar(spatial, x="district", y="score")

    assert sklearn.__version__
    assert spatial.crs.to_epsg() == 4326
    assert len(figure.data) == 1
