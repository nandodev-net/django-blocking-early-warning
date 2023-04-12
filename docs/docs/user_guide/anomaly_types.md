# Anomaly Types

The Early Warning System aims to help you to **catch possible blocking events earlier**. In order to do so, it will run some analysis 
over recent sets of measurements in order to find something strange. In this section we will learn which kind of events might trigger 
an anomaly.

There's two main types of anomaly that the analyzer looks for, **spikes** and **coninuous blocking**. "Spikes" represent a sudden increment
in anomalies for a given url, while "continuous blocking" represents an event where the affected URL is consistently unreachable for extended 
periods of time.   

The process that looks for these events runs periodically, and if it founds some of these anomalies, then it will send an email notification
if the url is marked with a high enough alert level and if some email is provided.

