from datetime import datetime, timedelta, time
from django.shortcuts import render
from django.views.generic import TemplateView, View
from django.http import HttpResponse, HttpRequest, HttpResponseBadRequest, JsonResponse
from requests import Response
from blocking_early_warnings.settings import DATE_FORMAT

# Local imports
from blocking_early_warnings.utils.histogram_generator import HistogramGenerator
from django.core.paginator import Paginator
from .models import Metric, Url
from .raw_queries import raw_metric_name, raw_url_name, get_datatable
from django.db.models import Max, Q, F, Subquery, OuterRef
from django.db.models.functions import TruncDate
from django.db import connection




def datatable_paginado(request):

    today = datetime.now().date()
    fecha_antier = today - timedelta(days=2)
    fecha_ayer = today - timedelta(days=1)

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
        )
        SELECT
            metric.id,
            metric.url_id,
            metric.measurement_count,
            metric.anomaly_count,
            metric.asn_id,
            metric.hour,
            url.url
        FROM
            filtered_metrics AS metric
        JOIN blocking_early_warnings_url AS url ON metric.url_id = url.id
        ORDER BY metric.anomaly_count DESC;
    """

    # Ejecuta la consulta SQL
    with connection.cursor() as cursor:
        cursor.execute(raw_sql)
        column_names = [col[0] for col in cursor.description]
        combined_queryset = [
            dict(zip(column_names, row))
            for row in cursor.fetchall()
        ]


    paginator = Paginator(combined_queryset, 20) # Muestra 20 registros por página

  

    page = request.GET.get('page')
    datos_paginados = paginator.get_page(page)
 
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