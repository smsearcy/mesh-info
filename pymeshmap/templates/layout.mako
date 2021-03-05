<!DOCTYPE html>
<html lang="${ request.locale_name }">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="aredn wireless mesh network map">
  <meta name="author" content="Scott Searcy">
  <link rel="shortcut icon" href="${ request.static_url('pymeshmap:static/pymeshmap-16x16.png') }">

  <title>
    <%block name="title">
      pyMeshMap
    </%block>
  </title>

  <link rel="stylesheet" href="${ request.static_url('pymeshmap:static/css/bulma.min.css')}">

</head>

<body>
<div id="app">

<nav class="navbar is-dark" role="navigation" aria-label="main navigation">
  <div class="navbar-brand">
    <a class="navbar-item" href="${ request.route_path('home') }">
      <img src="${ request.static_url('pymeshmap:static/pymeshmap-32x32.png') }" width="32" height="32">
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
      <a class="navbar-item" href="${ request.route_path('home') }">
        Overview
      </a>
      <a class="navbar-item is-disabled">
        Nodes
      </a>
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
<script src="${ request.static_url('pymeshmap:static/js/vue.global.prod.js') }"></script>
<script src="${ request.static_url('pymeshmap:static/js/meshmap.js') }"></script>
<%block name="javascript"></%block>

</body>
</html>
