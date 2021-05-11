<%inherit file="layout.mako"/>

<%block name="title">${ node.name }</%block>

<div class="container">
  <h1 class="title">${ node.name }</h1>
  <div class="content">
    ${ node.description}
  </div>
  <h2 class="subtitle">Details</h2>

  <h2 class="subtitle">Links</h2>
  <table class="table">
    <thead>
    <tr>
      <th>Name</th>
      <th>Status</th>
      <th>Type</th>
      <th><abbr title="Signal to Noise Ratio">SNR</abbr></th>
      <th><abbr title="Link Quality">LQ</abbr></th>
      <th><abbr title="Neighbor Link Quality">NLQ</abbr></th>
      <th>Link Cost</th>
      <th>Bearing</th>
      <th>Distance</th>
      <th>Last Seen</th>
    </tr>
    </thead>
    <tbody>
    % for link in node.links:
      <tr>
        <td>
          <a href="${ req.route_url("node", id=link.destination_id}) }">
            ${ link.destination.name }
          </a>
        </td>
        <td>${ link.status }</td>
        <td>${ link.type.name.title() }</td>
        <td>${ link.signal_noise_ratio }</td>
        <td>${ link.quality }</td>
        <td>${ link.neighbor_quality }</td>
        <td>${ link.olsr_cost }</td>
        <td>${ link.bearing }</td>
        <td>${ link.distance }</td>
        <td>${ link.last_seen }</td>
      </tr>
    % endfor
    </tbody>
  </table>
</div>
