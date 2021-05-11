<%inherit file="layout.mako"/>

<%block name="title">Nodes</%block>

<div class="container">
  <h1 class="title">Nodes</h1>
  <table class="table is-striped is-narrow">
    <thead>
    <tr>
      <th>Name</th>
      <th>Status</th>
      <th>Band</th>
      <th>Services</th>
      <th>Links</th>
      <th>Tunnel Installed</th>
      <th>Tunnel Count</th>
      <th>Up Time</th>
      <th>Last Seen</th>
      <th>WLAN IP</th>
      <th>Firmware Version</th>
      <th>API Version</th>
      <th>Location</th>
    </tr>
    </thead>
    <tbody>
    % for node in nodes:
      <tr>
        <td>${ node.name }</td>
        <td>${ node.status }</td>
        <td>${ node.band }</td>
        <td>${ len(node.services) }</td>
        <td>${ len(node.links) }</td>
        <td>${ 'Yes' if node.tunnel_installed else 'No' }</td>
        <td>${ node.active_tunnel_count }</td>
        <td>${ node.up_time }</td>
        <td>${ node.last_seen }</td>
        <td>${ node.wlan_ip }</td>
        <td>${ node.firmware_version }</td>
        <td>${ node.api_version }</td>
        <td>${ node.location }</td>
      </tr>
    % endfor
    </tbody>
  </table>
</div>
