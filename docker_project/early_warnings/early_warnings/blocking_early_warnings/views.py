from datetime import datetime, timedelta, time
from django.shortcuts import render
from django.views.generic import TemplateView, View
from django.http import HttpResponse, HttpRequest, HttpResponseBadRequest, JsonResponse
from blocking_early_warnings.settings import DATE_FORMAT

# Local imports
from blocking_early_warnings.utils.histogram_generator import HistogramGenerator
from django.core.paginator import Paginator
from django.db import connection




def datatable_paginado(request):
    """
    Pagina y filtra los datos de una tabla en la base de datos y los muestra en una plantilla.
    Args:
        request (HttpRequest): Una solicitud HTTP que contiene información sobre la solicitud del usuario.
    Returns:
        HttpResponse: Una respuesta HTTP que contiene una plantilla HTML que muestra los datos de la tabla paginados y filtrados.
    Raises:
        DatabaseError: Si hay un error al ejecutar la consulta SQL en la base de datos.
    """

    def calculate_percentage(a: int, b: int) -> float:
        """
        Calcula el porcentaje que 'b' representa de 'a'.

        Args:
            a (int): El valor del cual se calcula el porcentaje.
            b (int): El valor que representa el porcentaje de 'a'.

        Returns:
            float: El porcentaje que 'b' representa de 'a', como un número de punto flotante.

        Raises:
            ZeroDivisionError: Si 'a' es igual a cero.
        """
        if a == 0:
            raise ZeroDivisionError("El valor de 'a' no puede ser cero.")
        else:
            percentage = (b / a) * 100
            if percentage.is_integer():
                return int(percentage)
            else:
                return round(percentage, 1)
        
    # Construye la consulta SQL
    raw_sql = """ 
        WITH ranked_metrics AS (
            SELECT *,
            ROW_NUMBER() OVER (PARTITION BY url_id, asn_id, date_trunc('day', hour) ORDER BY hour DESC) AS rank
            FROM blocking_early_warnings_metric
            WHERE hour::date IN (current_date - INTERVAL '2 days', current_date - INTERVAL '1 days')
        ),
        filtered_metrics AS (
            SELECT *
            FROM ranked_metrics
            WHERE rank = 1
        ),
        metrics_by_day AS (
            SELECT
                url_id,
                asn_id,
                COALESCE(MAX(CASE WHEN hour::date = current_date - INTERVAL '2 days' THEN anomaly_count END), 0) AS anomaly_count_2_days_ago,
                COALESCE(MAX(CASE WHEN hour::date = current_date - INTERVAL '2 days' THEN measurement_count END), 0) AS measurement_count_2_days_ago,
                MAX(CASE WHEN hour::date = current_date - INTERVAL '2 days' THEN hour END) AS hour_2_days_ago,
                COALESCE(MAX(CASE WHEN hour::date = current_date - INTERVAL '1 days' THEN anomaly_count END), 0) AS anomaly_count_1_days_ago,
                COALESCE(MAX(CASE WHEN hour::date = current_date - INTERVAL '1 days' THEN measurement_count END), 0) AS measurement_count_1_days_ago,
                MAX(CASE WHEN hour::date = current_date - INTERVAL '1 days' THEN hour END) AS hour_1_days_ago
            FROM filtered_metrics
            GROUP BY url_id, asn_id
        ),
        results AS (
            SELECT
                url.url,
                asn.code AS asn_code,
                asn.name AS asn_name,
                metrics.asn_id,
                metrics.anomaly_count_2_days_ago,
                metrics.measurement_count_2_days_ago,
                metrics.hour_2_days_ago,
                metrics.anomaly_count_1_days_ago,
                metrics.measurement_count_1_days_ago,
                metrics.hour_1_days_ago
            FROM
                metrics_by_day AS metrics
            JOIN blocking_early_warnings_url AS url ON metrics.url_id = url.id
            JOIN blocking_early_warnings_asn AS asn ON metrics.asn_id = asn.id
        )
        SELECT * FROM results
        ORDER BY anomaly_count_1_days_ago DESC;
    """

    # Ejecuta la consulta SQL
    with connection.cursor() as cursor:
        cursor.execute(raw_sql)
        column_names = [col[0] for col in cursor.description]
        combined_queryset = [
            dict(zip(column_names, row))
            for row in cursor.fetchall()
        ]
    
    # Pagina los resultados y los almacena en la variable 'datos_paginados'
    paginator = Paginator(combined_queryset, 10)
    page = request.GET.get('page')
    datos_paginados = paginator.get_page(page)

    # calculando los porcentajes de una pagina de metricas
    for obj in datos_paginados:
        obj['percentage_2_days_ago'] = calculate_percentage(
            obj['measurement_count_2_days_ago'],
            obj['anomaly_count_2_days_ago']
            )
        obj['percentage_1_days_ago'] = calculate_percentage(
            obj['measurement_count_1_days_ago'],
            obj['anomaly_count_1_days_ago']
        )

    # Renderiza la plantilla 'webpage/datatable.html' con los resultados paginados
    return render(request, 'webpage/datatable.html', {'datos_paginados': datos_paginados})



class HistogramPageView(TemplateView):
    """view to display histograms with retrieved data from ooni
    """

    template_name: str = "webpage/index.html"


class HistogramBackendView(View):
    """View to compute the data required to fill the main histogram template view
    """

    def get(self, request : HttpRequest) -> HttpResponse:
        """A get request returning a json response delivering the required data to fill the histogram table

        Args:
            request (HttpRequest): A request providing the following arguments:
                - start_date : str = a date to start counting measurements. If not provided, defaults to 24 hours before end_date
                - end_date : str = a date to finish counting measurements. If not provided, defaults to now.
                - asn : str = asn code for an internet provider. If not provided, don't filter by asn
                - url : str = url for a site. If not provided, don't filter by url
                
        Returns:
            HttpResponse: A json response providing the following fields:
                - date_format : str = date format used to express dates in strings
                - url : Optional[str] = site url if provided as input
                - asn : Optional[str] = ASN code if provided as input
                - histogram : [object] = A list of objects for the histogram blocks, with the following format:
                    - hour : datetime = hour value for this block
                    - total_count : int = how many measurements for this hour
                    - anomaly_count : int = how many anomalies for this block
        """

        # Parse input from request
        args = request.GET

        start_date = args.get("start_date")
        end_date = args.get("end_date")
        asn = args.get("asn")
        url = args.get("url")

        # Try to parse date into datetimes
        if start_date is not None:
            try:
                start_date = datetime.strptime(start_date, DATE_FORMAT)
            except ValueError as e:
                return HttpResponseBadRequest(f"Invalid start_date format. Expected format: {DATE_FORMAT}")

        if end_date is not None:
            try:
                end_date = datetime.strptime(end_date, DATE_FORMAT)
            except ValueError as e:
                return HttpResponseBadRequest(f"Invalid end_date format. Expected format: {DATE_FORMAT}")
        
        # Compute histogram content
        histo = HistogramGenerator.histogram(url, asn, start_date, end_date) 

        return JsonResponse(data={
            "date_format" : DATE_FORMAT,
            "url" : url, 
            "asn" : asn,
            "histogram" : [
                {
                    "hour" : datetime.strftime(b.hour, DATE_FORMAT),
                    "total_count" : b.total_count,
                    "anomaly_count" : b.anomaly_count,
                    "ok_count" : b.total_count - b.anomaly_count
                } 
                for b in histo
            ]
        })