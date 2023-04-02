from .models import Metric, Url, Site

raw_url_name, raw_metric_name, raw_site_name = Url._meta.db_table, Metric._meta.db_table, Site._meta.db_table



get_datatable2 = f"SELECT \
  u.url AS URL, \
  m_antier.measurement_count AS ultima_medicion_antier, \
  m_antier.anomaly_count AS total_fallas_antier, \
  m_ayer.measurement_count AS ultima_medicion_ayer, \
  m_ayer.anomaly_count AS total_fallas_ayer \
FROM {raw_url_name} u \
LEFT JOIN ( \
  SELECT URL, measurement_count, anomaly_count \
  FROM {raw_metric_name} \
  WHERE hour = date_trunc('day', CURRENT_DATE - INTERVAL '2 days') \
  ORDER BY hour DESC \
  LIMIT 1 \
) m_antier ON u.nombre = m_antier.URL \
LEFT JOIN ( \
  SELECT URL, measurement_count, anomaly_count \
  FROM {raw_metric_name} \
  WHERE hour = date_trunc('day', CURRENT_DATE - INTERVAL '1 day') \
  ORDER BY hour DESC \
  LIMIT 1 \
) m_ayer ON u.nombre = m_ayer.URL;"

