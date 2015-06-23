
Project thay includes diverse developments around testing,
monitoring, verifying and deploying solutions around
Junos PyEz and Juniper Networks products.

Junos PyEz will be cornerstone for all scripts, but other
auxiliary libraries and concepts will be included, such
as the InfluxDB API, Grafana etc.

## Subprojects:

### Junos TE++ monitoring script:

This python monitoring script mainly leverages Junos PyEz and InfluxDB Python APIs to provide a monitoring toolset for the Junos 14.2+ RSVP-TE++ Phase 1 (dynamic BW mgmt using container LSPs) implementation, as described under:
* http://www.juniper.net/documentation/en_US/junos14.2/topics/concept/dynamic-bandwidth-management-overview.html
* http://www.juniper.net/documentation/en_US/junos14.2/topics/example/example-dynamic-bandwidth-management-using-mp-lsp-configuring.html
* "Maximize Bandwidth Utilization with Juniper Networks TE++" whitepaper (http://www.juniper.net/assets/us/en/local/pdf/whitepapers/2000587-en.pdf)

This monitoring toolset provides KPI tracing for self-detected BW consumption as per auto-bandwidth statistics, but also traces as well effectively measured absolute packets and bytes per (sub)LSP, so that delta values can be displayed as well with a GUI such as Grafana. Also, effectively signalled BW reservation values are traced per LSP (changing on a per auto-bandwidth adjust-interval for LSPs or aggregate values for the container-LSP) and logical input interface absolute and relation stats are obtained for comparison purposes.

This script has been designed based on the following building blocks:
* Remote connectivity to DUT via SSH port forwarding. Handling NETCONF connection over them as explained under:
http://forums.juniper.net/t5/Automation/Junos-NETCONF-and-SSH-tunneling-Part-1/ba-p/215093
http://forums.juniper.net/t5/Automation/Junos-NETCONF-and-SSH-tunneling-Part-2/ba-p/215307
* Basic argparsing for container-LSP name, forwarded port, test period and sampling interval
* Jinja2 templates for YAML files including OpTables and OpViews to obtain fields from the following generic Xpaths:
   <get-mpls-container-lsp-information> <extensive>
      rsvp-session-data/rsvp-session/mpls-lsp
      rsvp-session-data/mpls-container-lsp
   <get-mpls-container-lsp-information> <statistics>
      rsvp-session-data/rsvp-session/mpls-lsp
   and others
* Simple flow and error control to connect to DUT with Junos PyEz 
* Creation of (and removal of previous) InfluxDB local database to store values in a scaled fashion. KPI values stored as JSONs in InfluxDB
* Basic programmatic steps to sysexit() or move forward
* Logging/debugging facility

These are sample screenshots from Grafana after scanning and averaging InfluxDB series created by the script:
![](https://github.com/go-nzo/automated_testing/blob/master/junos-te-plus-plus-monitor/grafana-screenshots/Grafana_screenshot1.png)
![](https://github.com/go-nzo/automated_testing/blob/master/junos-te-plus-plus-monitor/grafana-screenshots/Grafana_screenshot2.png)
![](https://github.com/go-nzo/automated_testing/blob/master/junos-te-plus-plus-monitor/grafana-screenshots/Grafana_screenshot3.png)
![](https://github.com/go-nzo/automated_testing/blob/master/junos-te-plus-plus-monitor/grafana-screenshots/Grafana_screenshot4.png)
![](https://github.com/go-nzo/automated_testing/blob/master/junos-te-plus-plus-monitor/grafana-screenshots/Grafana_screenshot5.png)


