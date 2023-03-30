from .models import Metric, Url, Site

raw_url_name, raw_metric_name, raw_site_name = Url._meta.db_table, Metric._meta.db_table, Site._meta.db_table


get_datatable = '''
WITH urls AS (
  SELECT url FROM blocking_early_warnings_url
)
SELECT urls.url, m1.measurement_count, m1.anomaly_count, m1.hour AS yesterday_hour, m2.measurement_count, m2.anomaly_count, m2.hour AS day_before_yesterday_hour
FROM urls
LEFT JOIN blocking_early_warnings_metric AS m1 ON urls.url = m1.metric_url AND DATE_TRUNC('day', m1.hour) = DATE_TRUNC('day', NOW() - INTERVAL '1 day')
LEFT JOIN blocking_early_warnings_metric AS m2 ON urls.url = m2.metric_url AND DATE_TRUNC('day', m2.hour) = DATE_TRUNC('day', NOW() - INTERVAL '2 day')
WHERE m1.measurement_count IS NOT NULL
GROUP BY urls.url, m1.measurement_count, m1.anomaly_count, m1.hour, m2.measurement_count, m2.anomaly_count, m2.hour;




'''

# # subconsulta para obtener los últimos registros de mediciones de la fecha antier
# subconsulta_antier = Subquery(
#     main_query.filter(metric__hour__date=fecha_antier).values('metric__hour__date')\
#         .annotate(date_time=Max('metric__hour'))\
#             .values('metric__anomaly_count', 
#                     'metric__measurement_count',
#                     'date_time'
#                     ))

# # subconsulta para obtener los últimos registros de mediciones de la fecha ayer
# subconsulta_ayer = Subquery(
#     main_query.filter(metric__hour__date=fecha_ayer).values('metric__hour__date')\
#         .annotate(date_time=Max('metric__hour'))\
#             .values('metric__anomaly_count', 
#                     'metric__measurement_count',
#                     'date_time'
#                     ))

    # queryset = Url.objects.filter(metric__measurement_count__isnull=False)\
    #     .filter(metric__hour__date__in=past_two_days).values('metric__hour__date')\
    #         .annotate(record=Max('metric__hour'))\
    #             .values('url',
    #                     'metric__asn__code',
    #                     'metric__anomaly_count', 
    #                     'metric__measurement_count',
    #                     'record'
    #                     ).order_by('url')

    # subconsulta para obtener los últimos registros de mediciones de la fecha antier
    # subconsulta_antier = Subquery(
    #     main_query.filter(hour__date=fecha_antier).values('hour__date')\
    #         .annotate(date_time=Max('hour'))\
    #             .values('anomaly_count', 
    #                     'measurement_count',
    #                     'date_time'
    #                     ))



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
