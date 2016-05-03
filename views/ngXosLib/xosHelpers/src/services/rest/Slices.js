(function() {
  'use strict';

  angular.module('xos.helpers')
  /**
  * @ngdoc service
  * @name xos.helpers.Slices
  * @description Angular resource to fetch Slices
  **/
  .service('Slices', function($resource){
    return $resource('/api/core/slices/:id/', { id: '@id' }, {
      update: { method: 'PUT' },
    });
  })
})();