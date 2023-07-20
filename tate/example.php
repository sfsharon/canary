<!DOCTYPE html>
<html>
<head>
<title>MySQL Testing</title>
</head>
<body>
<h1>MySQL Working Around !!!</h1>

<?php
// Connect to the MySQL database
$conn = mysqli_connect("localhost", "root", "", "tate");

// Check the connection
if ($conn->connect_error) {
  die("Connection failed: " . $conn->connect_error);
}

// Get the query results
$sql = "SELECT testbed,sw_ver,duration,started,pass,fail FROM jobs WHERE (started >= curdate() - interval 1 year AND testbed = 'Edgecore-pc3026' AND sw_ver LIKE 'develop.8.0.0_5%') ORDER BY started DESC";
$results = mysqli_query($conn, $sql);

// Display the query results
if ($results) {
  echo "<table>";
  while ($row = mysqli_fetch_assoc($results)) {
    echo "<tr>";
    foreach ($row as $key => $value) {
      echo "<td>" . $value . "</td>";
    }
    echo "</tr>";
  }
  echo "</table>";
} else {
  echo "No results found.";
}

// Close the connection
mysqli_close($conn);
?>

</body>
</html>
