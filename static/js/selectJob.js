function getSelectedJob(){

  var ul = document.getElementById("selectable_jobs"),id;
  var items = ul.getElementsByTagName("li");

  for(var i = 0; i < items.length; i++)
  {
      items[i].onclick = function()
      {

          id = this.id;

          $.ajax({

          type: "POST",

          headers: {'content-type': 'application/json'},

          data : JSON.stringify({ "id": id }),

          url: "/jobs_list",

          dataType: "json",

          timeout: 5000,

          success: function (resp) {
            var industry_arr = [];
            var job_functions_arr = [];
            var skills_arr = [];
            var skills_arr_2 = [];

            $('#title').html(resp['title']);
            $('#company').html(resp['company']);
            $('#description').html(resp['description']);
            $('#dop').html(resp.dop);
            for(var i = 0; i < resp['industry'].length; i++)
            {
                industry_arr.push(resp['industry'][i]['name'] + "</br>");
            }
            $('#industry').html(industry_arr);
            $('#employment_type').html(resp['employment_type']);
            for(var i = 0; i < resp['job_functions'].length; i++)
            {
                job_functions_arr.push(resp['job_functions'][i]['type'] + "</br>");
            }
            $('#functions').html(job_functions_arr);
            $('#education').html(resp['education'][0]['name']);
            $.each(resp['skills'],function(index, value){
                        num_of_skills = resp['skills'].length;

                        if(index < num_of_skills / 2){
				            skills_arr.push('<li class="list-group-item" id="skills">' + value['name'] + '</li>');
				        } else {
				            skills_arr_2.push('<li class="list-group-item" id="skills">' + value['name'] + '</li>');
				        }
            });
            $('#skills').html(skills_arr);
            $('#skills_2').html(skills_arr_2);
            $('.apply_btn').html('<button type="button" class="btn btn-primary btn-md apply_button" onclick="apply();"' + 'id="id_' + id + '">' + 'Apply' + '</button>');
//            $('#job_num').html(id);
          },
          error: function (parsedjson, textStatus, errorThrown) {

          console.log(textStatus)
          }
        });

      };
  }
}

function apply(){

  var id = document.getElementsByClassName("apply_button")[0].id;

  $.ajax({

  type: "POST",

  headers: {'content-type': 'application/json'},

  data : JSON.stringify({ "id": id }),

  url: "/applicants",

  dataType: "json",

  timeout: 5000,

  success: function (resp) {
    console.log(id);
    window.location = "/applicants";
  },
  error: function (parsedjson, textStatus, errorThrown) {

  console.log(textStatus);
  }
});
}

