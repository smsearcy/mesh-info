<%inherit file="layout.mako"/>
<div class="container">
  <h1 class="title">Local Mesh</h1>
  <div class="columns">
    <div class="column">
      <div class="card">
        <header class="card-header">
          <p class="card-header-title">Mesh Overview</p>
        </header>
        <div class="card-content">
          <div class="content">
            <table class="table">
              <tbody>
              <tr>
                <th>Node Count:</th>
                <td>${ f"{node_count:,d}" }</td>
              </tr>
              <tr>
                <th>Link Count:</th>
                <td>${ f"{link_count:,d}" }</td>
              </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
    <div class="column">
      <div class="card">
        <header class="card-header">
          <p class="card-header-title">Poller Statistics</p>
        </header>
        <div class="card-content">
          <div class="content">
          %if last_run is not None:
            <table class="table">
              <tbody>
              <tr>
                <th>Last Ran:</th>
                <td>${ last_run.started_at }</td>
              </tr>
              <tr>
                <th>Node Count:</th>
                <td>${ last_run.node_count }</td>
              </tr>
              <tr>
                <th>Link Count:</th>
                <td>${ last_run.link_count }</td>
              </tr>
              <tr>
                <th>Polling Time:</th>
                <td>${ duration(last_run.polling_duration) }</td>
              </tr>
              <tr>
                <th>Total Run Time:</th>
                <td>${ duration(last_run.total_duration) }</td>
              </tr>
              <tr>
                <th>Error Count:</th>
                <td>${ last_run.error_count }</td>
              </tr>
              </tbody>
            </table>
          %else:
            <div class="notification is-warning">
              The poller has not ran/finished yet.
            </div>
          %endif
          </div>
        </div>
        <div class="card-image"></div>
      </div>
    </div>
  </div>

</div>

<%def name="duration(value)">
  %if value > 120:
    ${ value / 60}m
  %else:
    ${ value }s
  %endif
</%def>
