{% load generator_extras %}
{% for cve in cves %}
* Fix for {{ cve }} merged in {{ hash }}.
{% endfor %}
