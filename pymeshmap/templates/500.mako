<%inherit file="layout.mako"/>
<div class="container">
  <h1 class="title">500 <span class="subtitle">Server Error</span></h1>
  <div class="notification is-danger is-light">
    <p>${ message }</p>
    <p>Please contact the site admin and let them know you saw this at ${ timestamp.strftime("%Y-%m-%d %H:%M:%S") } so they can review the logs.</p>
  </div>
</div>
