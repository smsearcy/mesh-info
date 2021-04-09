<!DOCTYPE html>
<html lang="${ req.locale_name }">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="aredn wireless mesh network map">
  <link rel="shortcut icon" type="image/png" sizes="16x16" href="${ req.static_url('pymeshmap:static/mesh-network-16x16.png') }">
  <link rel="shortcut icon" type="image/png" sizes="32x32" href="${ req.static_url('pymeshmap:static/mesh-network-32x32.png') }">

  <title>
    <%block name="title">
      pyMeshMap
    </%block>
  </title>

  <link rel="stylesheet" href="${ req.static_url('pymeshmap:static/css/bulma.min.css')}">

</head>

<body>
<div id="app">

<nav class="navbar is-dark" role="navigation" aria-label="main navigation">
  <div class="navbar-brand">
    <a class="navbar-item" href="${ req.route_path('home') }">
      <img src="${ req.static_url('pymeshmap:static/mesh-network-32x32.png') }" width="32" height="32">
    </a>

    <a role="button" class="navbar-burger" aria-label="menu" aria-expanded="false" data-target="navbarMeshMap"
       @click="toggleMenu" :class="{'is-active': menuExpanded}">
      <span aria-hidden="true"></span>
      <span aria-hidden="true"></span>
      <span aria-hidden="true"></span>
    </a>
  </div>

  <div id="navbarMeshMap" class="navbar-menu" :class="{'is-active': menuExpanded}">
    <div class="navbar-start">
      % for label, route in [("Overview", "home"), ("Nodes", "nodes")]:
        <a class="navbar-item ${ 'is-active' if getattr(req.matched_route, 'name', '') == route else '' }"
           href="${ req.route_path(route) }">
          ${ label }
        </a>
      % endfor
      <a class="navbar-item is-disabled">
        Map
      </a>
    </div>

    <div class="navbar-end">
      <div class="navbar-item">
        <div class="buttons">
          <a class="button is-light is-invisible">Log in</a>
        </div>
      </div>
    </div>
  </div>
</nav>

<section class="section">
  ${ next.body() }
</section>

</div>

## TODO: Switch Vue.js file based on environment?
<script src="${ req.static_url('pymeshmap:static/js/vue.global.prod.js') }"></script>
<script src="${ req.static_url('pymeshmap:static/js/meshmap.js') }"></script>
<%block name="javascript"></%block>

</body>
</html>
