(function() {
  'use strict';

  angular.module('xos.helpers')
  /**
  * @ngdoc service
  * @name xos.helpers.Flavors
  * @description Angular resource to fetch Flavors
  **/
  .service('Flavors', function($resource){
    return $resource('/api/core/flavors/:id/', { id: '@id' }, {
      update: { method: 'PUT' },
    });
  })
})();