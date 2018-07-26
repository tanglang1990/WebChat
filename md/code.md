### 代码片段

图片选择样及html代码
```css
  #img_pre {
    width: 1.8rem;
    height: 1.8rem;
    background-size: 100% 100%;
    background-image: url("{{ static_url('img/img_add.png') }}");
  }
```
```html
<div class="aui-list-item-input">
  <label for="head_img_id" class="aui-pull-right">
    <div id="img_pre"></div>
  </label>
  <input id="head_img_id" type="file" name="head_img" style="display: none">
</div>

<script src='{{ static_url("js/jquery-2.1.4.min.js") }}'></script>
<script>
    $(function () {
        $("input[type='file']").change(function () {
            var reader = new FileReader()
            reader.onload = function (e) {
                $("#img_pre").css("background-image", "url(" + e.target.result + ")")
            }
            reader.readAsDataURL(this.files[0]);
        })
    });
</script>
```